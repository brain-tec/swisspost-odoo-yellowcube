In order to be able to use the php script, the next steps must be followed:

1. initialize the submodule wse-php, by running the next shell command on the repo main dir: **git submodule update --init** (if not working use: **git submodule status pc_connect_warehouse_yellowcube_soap/wse-php**)
   (if this doesn't work, check out this repo: https://github.com/robrichards/wse-php/tree/06967a95515a79ed48607c927482dcda36e48b9c')
2. run the next order (It must fail, as the path to the keyis missing): **php5 sign.php < sign.txt**
3. The return error must be: **PHP Fatal error:  Uncaught exception 'Exception' with message 'Failure Signing Data:**
