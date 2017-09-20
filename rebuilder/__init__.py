# -*- coding: utf-8 -*-

import argparse
import logging
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from shlex import quote
from urllib.parse import urlparse


ToolSet = namedtuple('ToolSet', ['rpkg', 'koji'])


TOOLS = {
    'pkgs.devel.redhat.com': ToolSet('rhpkg', 'brew'),
    'pkgs.fedoraproject.org': ToolSet('fedpkg', 'koji'),
}
DIM = '\033[2m'
RESET = '\033[0m'

TASK_ID_RE = re.compile(r'^Created task: (\d+)$', re.IGNORECASE)


def run(*args, **kwargs):
    try:
        print(DIM, end='', flush=True)
        cp = subprocess.run(*args, **kwargs)
        return cp
    finally:
        print(RESET, end='', flush=True)


def switch_branch(logger, branch, orig=None):
    logger.info('$ git checkout %s', branch)
    run(['git', 'checkout', branch], check=True)
    if orig:
        proc = run(['git', 'diff', branch, orig],
                   check=True, stdout=subprocess.PIPE)
        if proc.stdout:
            logger.info('$ git reset --hard %s', orig)
            run(['git', 'reset', '--hard', orig], check=True)


def get_current_branch():
    proc = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
               stdout=subprocess.PIPE, check=True)
    return proc.stdout.decode('utf-8').strip()


def get_toolset(branch):
    proc = run(['git', 'config', '--get', 'branch.%s.remote' % branch],
               stdout=subprocess.PIPE, check=True)
    remote = proc.stdout.decode('utf-8').strip()
    proc = run(['git', 'remote', 'get-url', remote],
               stdout=subprocess.PIPE, check=True)
    url = proc.stdout.decode().strip()
    return TOOLS[urlparse(url).netloc.split('@', -1)[-1]]


def get_build_id(log_file):
    for line in log_file:
        m = TASK_ID_RE.match(line.decode('utf-8').strip())
        if m:
            return m.groups()[0]
    raise RuntimeError('No task id found.')


def toolset_build(logger, opts, args):
    failed = 0
    orig_branch = get_current_branch()
    rebase_on = orig_branch if not opts.no_rebase else None
    toolset = get_toolset(orig_branch)
    cmd = [toolset.rpkg] + args
    task_ids = []
    try:
        for branch in opts.branches:
            with tempfile.NamedTemporaryFile() as log_file:
                switch_branch(logger, branch, rebase_on)
                logger.info('$ %s' % ' '.join(cmd))
                run(['script', '-q', '-e', log_file.name,
                     '-c', ' '.join(quote(c) for c in cmd)],
                    check=True)

                try:
                    task_ids.append(get_build_id(log_file))
                except RuntimeError as exc:
                    logger.error(str(exc))

        if task_ids:
            logger.info('$ %s watch-task %s', toolset.koji, ' '.join(task_ids))
            proc = run([toolset.koji, 'watch-task'] + task_ids)
            if proc.returncode != 0:
                logger.error('Some packages failed to build successfully.')
                failed += 1
        else:
            logger.warning('No tasks to watch.')
            failed += 1
    finally:
        switch_branch(logger, orig_branch)

    return failed


def handle_build(logger, opts):
    return toolset_build(logger, opts, ['build', '--nowait'])


def handle_scratch(logger, opts):
    args = ['scratch-build', '--nowait']
    if opts.srpm:
        args.append('--srpm')
    return toolset_build(logger, opts, args)


def handle_mock(logger, opts):
    failed = 0
    orig_branch = get_current_branch()
    rebase_on = orig_branch if not opts.no_rebase else None
    toolset = get_toolset(orig_branch)
    cmd = [toolset.rpkg, 'mockbuild', '-N']
    try:
        for branch in opts.branches:
            switch_branch(logger, branch, rebase_on)
            logger.info('$ %s', ' '.join(cmd))
            proc = run(cmd)
            if proc.returncode != 0:
                logger.error('Failed to build for %s', branch)
                failed += 1
    finally:
        switch_branch(logger, orig_branch)

    return failed


def handle_release(logger, opts):
    proc = run(['rebuilder', 'scratch', '--srpm'] + opts.branches)
    if proc.returncode != 0:
        logger.error('SRPM scratch build failed')
        sys.exit(1)
    proc = run(['git', 'push', 'origin'] + opts.branches)
    if proc.returncode != 0:
        logger.error('Failed to push to dist-git')
        sys.exit(1)
    proc = run(['rebuilder', 'scratch'] + opts.branches)
    if proc.returncode != 0:
        logger.error('SCM scratch build failed')
        sys.exit(1)
    proc = run(['rebuilder', 'build'] + opts.branches)
    if proc.returncode != 0:
        logger.error('Build failed')
        sys.exit(1)


def get_parser():
    parser = argparse.ArgumentParser(
        description='rebuild package in many branches')

    parser.add_argument('--no-rebase', action='store_true')

    branch_parser = argparse.ArgumentParser(add_help=False)
    branch_parser.add_argument('branches', metavar='BRANCH', nargs='+')

    subparsers = parser.add_subparsers()

    build_parser = subparsers.add_parser('build', parents=[branch_parser])
    build_parser.set_defaults(func=handle_build)

    scratch_parser = subparsers.add_parser('scratch', parents=[branch_parser])
    scratch_parser.add_argument('--srpm', action='store_true')
    scratch_parser.set_defaults(func=handle_scratch)

    mock_parser = subparsers.add_parser('mock', parents=[branch_parser])
    mock_parser.set_defaults(func=handle_mock)

    release_parser = subparsers.add_parser('release', parents=[branch_parser])
    release_parser.set_defaults(func=handle_release)

    return parser


class ColorFormatter(logging.Formatter):
    def format(self, record):
        super().format(record)
        color = {
            logging.INFO: '\033[92m',
            logging.WARNING: '\033[93m',
            logging.ERROR: '\033[91m',
        }.get(record.levelno, '')
        return '%s%s%s' % (color, record.message, RESET)


def get_logger(out=None):
    out = out or sys.stdout
    handler = logging.StreamHandler(out)
    handler.setFormatter(ColorFormatter())
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def main():
    parser = get_parser()
    logger = get_logger()

    args = parser.parse_args()
    failed = args.func(logger, args)
    sys.exit(failed)
