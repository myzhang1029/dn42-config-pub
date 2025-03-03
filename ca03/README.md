# ca03 server

## Info
Mail server

## Packages
```
https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
git
postfix
opendkim
opendkim-tools
pypolicyd-spf
dovecot
fail2ban
```

Insert this SELinux module:
```
module my-auth 1.0;

require {
    type dovecot_auth_t;
    type faillog_t;
    class dir { add_name write };
    class file create;
}

#============= dovecot_auth_t ==============

allow dovecot_auth_t faillog_t:dir { add_name write };
allow dovecot_auth_t faillog_t:file create;
```
