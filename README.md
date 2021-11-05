# sis-api
## api-demo.py
A demo script showing how to use the SIS Webservices API

Note: This python script is not to be used in a production setting. Changes and additional error handling would be needed.

### Dependencies
  1. requests library. To install it run command:
    `pip3 install requests`

  2. Token files: Get a token by using the SIS UI > Your Account page > Get a Token and copy it to the file. File to be named as:
     - sis_test.token: Your SIS token for the test website. Needed if running the script to connect to the test site
     - sis_prod.token: Your SIS token for the production website. Needed if running the script to connect to the production site
  
  Limit read/write access to token file to only the user running the script and place it in the same directory as the script.
    
### Example usage
  - To get logger models from test
 
      `python3 api_demo.py test getloggermodel logger_models.csv`
      
  - To get equipment for 2 models AIRLINK GX440, CP-WAN-B311-A operated by SCSN-CA from test. Note that if modelname contains spaces it should be enclosed in quotes
      
      `python3 api_demo.py test getequipment equipment.csv --modelnames "AIRLINK GX440" CP-WAN-B311-A --operatorcodes SCSN-CA`
      
  - To refresh an existing token on test
      
      `python3 api_demo.py test --refreshtoken`

