In order to be able to use the connect transport api, following steps have to be
followed:

1. Install module
2. Create an external user, this one is allowed to use the service remotely. He
   has to be assigned to the group 'Connect Transport API Public'. Other 
   settings are not required.
3. Create an internal user and assign the user to the group 'Connect Transport 
   API Internal', this user has permission to access the 
    1. connect transport api
    2. connect transport log api
    3. stock connect file
4. In Menu 'Connect Transport API' create a new Connect Transport profile. The 
   name has to be unique. The 'Service Public User' has to be set to the 
   external user of step 2. The 'Service Internal User' has to be set to the 
   user of step 3.
   
To test the service use a REST client, for example Advanced REST client and 
carry out the following steps:

5. Authenticate:
   Send a post request to **'http://localhost:8069/web/session/authenticate'** with
   following 'application/json' content: 

    _**{"jsonrpc":"2.0",
     "id": "12345",
     "method": "call",
     "params": {
       "db": "db",
       "login": "connect_transport_extern",
       "password": "connect_transport_extern",
       "base_location": "http://localhost:8069",
       "session_id": "32323"
     }
    }**_

   'db' is the database you want to use, 'login' and 'password' are the 
   credentials from the extern user of step 2. 'base_location' is has to be 
   the same as from the URL. 'session_id' should be a unique number. The
   response of the request should be similar to this: 

   _**{
   "jsonrpc": "2.0",
   "id": "12345",
   "result": {
     "username": "connect_transport_extern",
     "user_context": {
       "lang": "en_US",
       "tz": "Europe/Zurich",
       "uid": 153
     },
     "db": "db",
     "uid": 153,
     "session_id": "32323"
   }
   }**_
   
   Make sure uid is a number (not _**"uid": false**_), otherwise the login was 
   not successful.
   
6. Create a stock connect file:
   Send following post request to **http://localhost:8069/transport_api_v1/create_stock_connect_file** 
   with following 'application/json' content (content has to be Base64 encoded):
   _**{
   "jsonrpc":"2.0",
   "id": "111112",
   "method": "call",
   "params": {
     "profile": "WBL profile",
     "filename":"test322dddds21",
     "content": "<<Base64 encoded content>>",
     "session_id": "32323"
   }
   }**_
   
   Make sure 'profile' matches with the name of profile in step 4. 'session' has
   to match with session_id used in step 5. 'filename' has to be unique, 
   otherwise an exception will be returned. If the request was successful, the 
   response to the request should be similar to this:
   _**{
   "jsonrpc": "2.0",
   "id": "111112",
   "result": {
     "status": "success",
     "id": 120
   }
   }**_
   
   The 'id' is the id from the created stock connect file.

7. In the Connect Transport API Logs all requests should appear (the content is
   Base64 decoded).
   