
#  EPEL7:  mcrypt, tidy, mssql, interbase, imap

%define def()	%%{!?_without_default:%%{!?_without_%1: %%global _with_%1 --with-%1}}

%{expand:%def imap}
%{expand:%def interbase}
%{expand:%def mcrypt}
%{expand:%def mssql}
%{expand:%def tidy}

%define list	%{?_with_mcrypt:mcrypt} %{?_with_tidy:tidy} %{?_with_mssql:mssql pdo_dblib} %{?_with_interbase:interbase pdo_firebird} %{?_with_imap:imap}
%define opts	%{?_with_interbase:--with-interbase=%{_libdir}/firebird --with-pdo-firebird=%{_libdir}/firebird} %{?_with_imap:--with-imap-ssl --with-kerberos}

Name:       php-extras
Summary:    Additional PHP modules from the standard PHP distribution
Version:    5.4.16
Release:    6%{?dist}
Group:      Development/Languages
License:    The PHP License
URL:        http://www.php.net/
Source0:    http://www.php.net/distributions/php-%{version}.tar.bz2

Patch0:     php-5.4.16-mcrypt.patch
# Sync with upstream extension in 5.6.26
Patch1:     php-5.4.16-pdo-dblib.patch

BuildRequires: php-devel >= 5.4
BuildRequires: php-pdo


%description
PHP is an HTML-embedded scripting language.

This package contains various additional modules for PHP, which
have not been included in the basic PHP package for Fedora Core.


%package -n php-imap
Summary:     A module for PHP applications that use IMAP
Group:       Development/Languages
Requires:    php(zend-abi) = %{php_zend_api}
Requires:    php(api) = %{php_core_api}
%{?_with_imap:BuildRequires: krb5-devel, openssl-devel, libc-client-devel}

%description -n php-imap
The php-imap package module will add IMAP (Internet Message Access Protocol)
support to PHP. IMAP is a protocol for retrieving and uploading e-mail messages
on mail servers. PHP is an HTML-embedded scripting language. If you need IMAP
support for PHP applications, you will need to install this package.


%package -n php-mcrypt
Summary:     Standard PHP module provides mcrypt library support
Group:       Development/Languages
Requires:    php(zend-abi) = %{php_zend_api}
Requires:    php(api) = %{php_core_api}
%{?_with_mcrypt:BuildRequires: libmcrypt-devel}

%description -n php-mcrypt
The php-mcrypt package contains a dynamic shared object that will
add support for using the mcrypt library to PHP.


%package -n php-tidy
Summary:     Standard PHP module provides tidy library support
Group:       Development/Languages
Requires:    php(zend-abi) = %{php_zend_api}
Requires:    php(api) = %{php_core_api}
%{?_with_tidy:BuildRequires: libtidy-devel}

%description -n php-tidy
The php-tidy package contains a dynamic shared object that will
add support for using the tidy library to PHP.


%package -n php-mssql
Summary: Standard PHP module provides mssql support
Group: Development/Languages
Requires:    php(zend-abi) = %{php_zend_api}
Requires:    php(api) = %{php_core_api}
Requires:    php(pdo-abi) = %{php_pdo_api}
Provides:    php_database
Provides:    php-pdo_dblib
Provides:    php-pdo_dblib%{?_isa}
%{?_with_mssql:BuildRequires: freetds-devel}

%description -n php-mssql
The php-mssql package contains a dynamic shared object that will
add MSSQL database support to PHP.  It uses the TDS (Tabular
DataStream) protocol through the freetds library, hence any
database server which supports TDS can be accessed.


%package -n php-interbase
Summary:     Standard PHP module provides interbase/firebird support
Group:       Development/Languages
Requires:    php(zend-abi) = %{php_zend_api}
Requires:    php(api) = %{php_core_api}
Requires:    php(pdo-abi) = %{php_pdo_api}
Provides:    php_database
Provides:    php-firebird
Provides:    php-firebird%{?_isa}
Provides:    php-pdo_firebird
Provides:    php-pdo_firebird%{?_isa}
%{?_with_interbase:BuildRequires: firebird-devel}

%description -n php-interbase
The php-interbase package contains a dynamic shared object that will
add database support through Interbase/Firebird to PHP.

InterBase is the name of the closed-source variant of this RDBMS that was
developed by Borland/Inprise.

Firebird is a commercially independent project of C and C++ programmers,
technical advisors and supporters developing and enhancing a multi-platform
relational database management system based on the source code released by
Inprise Corp (now known as Borland Software Corp) under the InterBase Public
License.


# Filter private shared
%{?filter_provides_in: %filter_provides_in %{_libdir}/.*\.so$}
%{?filter_setup}


%prep
%setup -q -n php-%{version}

%patch0 -p1 -b .security
%patch1 -p2 -b .dblib

# avoid tests which requires databases
rm -rf ext/{mssql,pdo_dblib,interbase,pdo_firebird}/tests


%build
for mod in %{list}
do
    pushd ext/$mod

    %{_bindir}/phpize
    %configure \
       --with-libdir=%{_lib} \
       %{opts} \
       --with-php-config=%{_bindir}/php-config

    make %{?_smp_mflags}

    popd
done


%check
fail=0
for mod in %{list}
do
    : Minimal load test for $mod extension
    php -d extension=ext/$mod/modules/$mod.so -m | grep -i $mod

    [ -d ext/$mod/tests ] || continue

    pushd ext/$mod

    : Upstream tests for $mod extension
    make test NO_INTERACTION=1 | tee rpmtests.log
    if grep -q "FAILED TEST" rpmtests.log
    then
        for t in tests/*.diff
        do
            echo "TEST FAILURE: $PWD/$t --"
            diff -u tests/$(basename $t .diff).exp tests/$(basename $t .diff).out || :
            fail=1
        done
    fi
    popd
done
exit $fail


%install
rm -rf %{buildroot}

install -d %{buildroot}%{php_extdir}
install -d %{buildroot}%{_sysconfdir}/php.d

for mod in %{list}
do
    make -C ext/${mod} install INSTALL_ROOT=%{buildroot}

    cat > %{buildroot}%{_sysconfdir}/php.d/${mod}.ini <<EOF
; Enable ${mod} extension module
extension=${mod}.so
EOF
    cat > files.${mod} <<EOF
%defattr(-,root,root)
%{php_extdir}/${mod}.so
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/php.d/${mod}.ini
EOF
done

%{?_with_mssql:cat files.pdo_dblib >>files.mssql}
%{?_with_interbase:cat files.pdo_firebird >>files.interbase}


%clean
rm -rf %{buildroot}


%define fil()	%%{?_with_%1:%%files -n php-%1 -f files.%1}
%{expand:%fil mcrypt}
%{expand:%fil tidy}
%{expand:%fil mssql}
%{expand:%fil interbase}
%{expand:%fil imap}


%changelog
* Tue Nov  8 2016 Remi Collet <rcollet@redhat.com> - 5.4.16-6
- pdo_dblib: sync with upstream from 5.6.26 #1381442 #1390201

* Tue Oct  4 2016 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.4.16-5
- Fix pdo dblib query (#1381442)

* Wed Mar  9 2016 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.4.16-4
- add dblib patch (#1266177)

* Thu Jan 30 2014 Remi Collet <rcollet@redhat.com> - 5.4.16-3
- mcrypt upstream security fix

* Wed Jan 22 2014 Remi Collet <rcollet@redhat.com> - 5.4.16-2
- drop interbase patch

* Thu Jan 16 2014 Remi Collet <rcollet@redhat.com> - 5.4.16-1
- add interbase
- add workaround for https://bugzilla.redhat.com/1054659
- minimal load test for all extensions

* Tue Jan 14 2014 Remi Collet <rcollet@redhat.com> - 5.4.16-0.1
- add mcrypt

* Tue Jan 14 2014 Remi Collet <rcollet@redhat.com> - 5.4.16-0
- update to 5.4.16
- add virtual provides for all provided extensions
- with imap, mssql, tidy

* Tue Sep 13 2011 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.3.3-1
- update to 5.3.3
- avoid explicit php dependencies in favour of php-api (#737956)

* Wed Dec 22 2010 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.3.2-3
- drop readline (now in the main php package)
- drop mhash (no more provided in php, hash used instead)
- spec file cleanup

* Tue Dec 21 2010 Nick Bebout <nb@fedoraproject.org> - 5.3.2-2
- Disable php-readline for now so we can get the rest built

* Sun Dec 19 2010 Jon Ciesla <limb@jcomserv.net> - 5.3.2-1
- Update for EL-6.

* Tue May 12 2009 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.6-5
- add pdo_dblib module for php-mssql
- add php-interbase support (both interbase and pdo_firebird modules)
  (initial patch from Remi Collet <fedora@famillecollet.com>)

* Wed Jun 20 2007 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.6-4
- add patch for mssql (#244736), a backport of some php-5.2 changes

* Fri Jun 15 2007 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.6-3
- add --with-libdir=%%{_lib} to handle 64bit arches properly

* Thu Jun 14 2007 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.6-2
- add php-mssql support

* Fri Sep  1 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.6-1
- update to 5.1.6

* Thu Jun 22 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.4-2
- auto-detect extdir and apiver again (needed for x86_64)

* Fri Jun 16 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.4-1
- update to upstream php 5.1.4
- an easier way to auto-detect php-api version
- specify extdir and apiver explicitly, because FE build system
  is not able to auto-detect it now.

* Fri Mar 31 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.2-3
- ppc arch hack: change dir before %%apiver auto-detecting

* Sat Mar 25 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.2-2
- Accepted for Fedora Extras
  (review by Tom "spot" Callaway <tcallawa@redhat.com>)
 
* Wed Mar  1 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.2-2
- more accurate Requires for the main php
  (using php-api, provided now by the Core php package).

* Tue Feb 28 2006 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.2-1
- update to 5.1.2
- replace readline patch (old issue go away and a new appears).
- apply well-known "libtool-rpath-workaround" (see in Internet ;-))
  to avoid use -rpath for linking

* Sat Dec 17 2005 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.1.1-1
- upgrade to 5.1.1 for FC5
- drop now missed "fam" and obsolete "sqlite" (sqlite2) modules

* Mon Nov 14 2005 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.0.4-1
- spec file cleanups

* Mon Oct 10 2005 Dmitry Butskoy <Dmitry@Butskoy.name> - 5.0.4-0
- adaptation for php5
- drop tests patch (no more needed).

* Fri Oct  7 2005 Dmitry Butskoy <Dmitry@Butskoy.name> - 4.3.11-0
- initial release
- create test stuff for check section. A lot of work because we play
  with extra modules by our own way...
- add patch to fix some pathes in tests
- add patch for readline configure

