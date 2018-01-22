# PC_AUDITTRAIL

## Known Issues

audittrail **doesnot supports RPC**, so any call made through RPC will never be logged using audittrail.

### TEST

As audittrail doesnot support RPC, it won't be possible to test it using the unittest framework.
Anyway, proper test are created, but **they will always fail**, until audittrail offers support for RPC.