from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
import urllib3
import csv
from datetime import datetime, timedelta
import json

# import webdriver
from selenium import webdriver
 
# create webdriver object
profile_path = '/home/karl/new_profile'
options=Options()
options.add_argument('-profile')
options.add_argument(profile_path)
driver = webdriver.Firefox(options=options)


def aspirationLogin(driver,login_email,login_pwd):
    driver.get("https://my.aspiration.com/auth/login/")
    time.sleep(5)
    emailField = driver.find_elements(By.ID, "signinEmail")
    pwdField = driver.find_elements(By.ID, "signinPassword")

    if len(emailField) > 1:
        raise Exception('Found more than one email field')

    if len(pwdField) > 1:
        raise Exception('Found more than one password field')

    emailField = emailField[0]
    pwdField = pwdField[0]

    emailField.send_keys(login_email)
    pwdField.send_keys(login_pwd)

    time.sleep(5)

    loginButton = driver.find_elements(By.CSS_SELECTOR, "button.btn-sapling")

    if len(loginButton) > 1:
        raise Exception('Found more than one login button')

    loginButton = loginButton[0]
    loginButton.click()

    time.sleep(5)

def callAPI(driver,account_number,start_date,end_date):
    cookies = driver.get_cookies()

    auth_token = None
    for x in cookies:
        if x['name'] == 'p_access_token':
            auth_token = x['value']

    request_headers = {
        'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://my.aspiration.com/new/accounts/spend/export',
        'Authorization': 'Bearer '+auth_token,
        'Content-Type': 'application/json',
        'Origin': 'https://my.aspiration.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'DNT': '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers'}
    http = urllib3.PoolManager()
    print("https://api.aspiration.com/v2/depository/"+account_number+"/transactions/csv?startDate="+start_date+"T00:00:00.000Z&finishDate="+end_date+"T00:00:00.000Z")
    response = http.request("GET",
                            "https://api.aspiration.com/v2/depository/"+account_number+"/transactions/csv?startDate="+start_date+"T00:00:00.000Z&finishDate="+end_date+"T00:00:00.000Z",
                            headers = request_headers)
    print(response.status)
    if response.status!=200:
        raise Exception('API request did not run successfully')
    return response.data
    

def writeAspirationCSV(driver,output_path,account_number,login_email,login_pwd,start_date,end_date):
    driver.get('https://my.aspiration.com/auth/login/')

    time.sleep(5)

    csvData = None
    try:
        csvData = callAPI(driver,account_number,start_date,end_date)
    except Exception:
        aspirationLogin(driver,login_email,login_pwd)
        csvData = callAPI(driver,account_number,start_date,end_date)

    csvStr = csvData.decode(encoding='utf-8')
    csvList = csvStr.split('\n')
    csvList = csv.DictReader(csvList)
    f = open(output_path,'w')
    w = csv.DictWriter(f,['Date','Payee','Amount','Tags'],quoting=csv.QUOTE_ALL)
    w.writeheader()

    for x in csvList:
        if x['Pending/posted']=='posted':
            w.writerow({'Date':x['Transaction date'],'Payee':x['Description'],'Amount':x['Amount']})

    f.close()

def uploadCSVToSimplifi(driver,csvPath,simplifiAccountCode):
    driver.get("https://app.simplifimoney.com")

    time.sleep(5)

    accountTarget = driver.find_elements(By.ID, simplifiAccountCode)

    if len(accountTarget) > 1:
        raise Exception('Found more than one bank account')

    accountTarget = accountTarget[0]
    accountTarget.click()

    time.sleep(5)

    transactionsTarget = driver.find_elements(By.ID, "transactions-import")

    if len(transactionsTarget) > 1:
        raise Exception('Found more than one upload button')

    transactionsTarget = transactionsTarget[0]
    transactionsTarget.click()

    time.sleep(5)

    csvTarget = driver.find_elements(By.ID, "import-csv")

    for x in csvTarget:
        if x.text!='':
            csvTarget = x
    
    csvTarget.click()

    time.sleep(5)

    fileTarget = driver.find_elements(By.XPATH, "//input[@type='file']")

    if len(fileTarget) > 1:
        raise Exception('Found more than one file upload button')

    fileTarget = fileTarget[0]

    fileTarget.send_keys(csvPath)

    importButton = driver.find_elements(By.XPATH,"//button[text()='IMPORT']")

    if len(importButton) > 1:
        raise Exception('Found more than one import button')

    importButton = importButton[0]
    importButton.click()

    time.sleep(20)
    #driver.quit()

d1 = datetime.today()
dateStr1 = d1.strftime('%Y-%m-%d')
d2 = datetime.today() - timedelta(days=7)
dateStr2 = d2.strftime('%Y-%m-%d')
timestamp = int(time.time())

configFile = open('/home/karl/bank_download_config.json')
config = json.loads(configFile.read())
configFile.close()
EMAIL = config['email']
PWD = config['pwd']
account_number = config['account_number']
simplifi_target = config['simplifi_target']
filePath = "/home/karl/bank_downloads/checking_out_"+dateStr1+'_'+str(timestamp)+".csv"
writeAspirationCSV(driver,filePath,account_number,EMAIL,PWD,dateStr2,dateStr1)
uploadCSVToSimplifi(driver,filePath,simplifi_target)
