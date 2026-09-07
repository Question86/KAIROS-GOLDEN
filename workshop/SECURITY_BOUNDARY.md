# Security boundary

The package seal detects drift; it is not an operating-system access control list. To make
the Workshop the only writer, deploy a dedicated service identity with write access to the
governed source and blueprint roots plus its state/transaction roots. Normal users, agents,
editors, and build tools receive read/execute access only. Retain a separately authenticated
recovery administrator.

`python workshop.py acl-plan` prints the exact boundary for a bound configuration and
changes nothing. The Workshop never changes ACLs, elevates privileges, or grants itself
direct SQL write authority. Test the boundary with a successful end-to-end transaction and
a restore drill before treating it as deployed.
