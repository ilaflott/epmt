This directory contains the following scripts

 * mk-release: Use this to create a release tarball (EPMT-x.y.z.tgz)
               This is only intended to be used by developers, not
               customers.

 * check-release: This script tests a release tarball (EPMT-x.y.z.tgz)
               It is only intended to be used by developers, not customer.

 * epmt-installer: This script installs a release tarball (EPMT-x.y.z.tgz)
               on a customer system. You should bundle this script alongside
               the release tarball and ship to the customer. You may also want
               to include `docs/Quickstart.md` in the package.


