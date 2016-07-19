# pc_connect_warehouse_yellowcube

## tests

### FDS

FDS test creates a dummy server on /tmp, unless the system parameter `test_fds_config` is set with a dictionary, such as next (in which case, it really connects to that server):


`{`  
`'server_url': 'localhost:22',`  
`'username': 'the_username',`  
`'password': 'the_long_secure_password',`  
`'rsa_key': None or 'the_base_64_rsa_key',`  
`}`  
