
    $ rebuilder scratch --srpm eng-rhel-6 eng-rhel-7
    $ rebuilder scratch master f25 f24 f23 epel7 el6
    $ rebuilder build master f25 f24

    $ rebuilder mockbuild eng-rhel-7 eng-rhel-6


# Process

1. Save current branch and rev
2. Find out environment
3. For each branch
   a. If not up-to-date, reset at rev
   b. Start build with --nowait
4. Gather task ids
5. Wait for tasks
6. Reset to original branch
