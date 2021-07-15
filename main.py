from typing import Optional
from fastapi import FastAPI
import time

from algosdk import account, encoding , mnemonic 
from algosdk.future.transaction import PaymentTxn
from algosdk.future.transaction import AssetConfigTxn
from algosdk.error import WrongChecksumError ,WrongMnemonicLengthError
from algosdk.v2client import algod , indexer

from schemes import * 

algod_client=algod.AlgodClient("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","http://localhost:4001") #Initializing the algod client
indexer_client=indexer.IndexerClient("","http://localhost:8980") #initializing the validator

app = FastAPI() #Create a base application instance


@app.get("/account/{Adress}")   
def get_account_info(Adress:str):              #Create a function that returns information about an account by its ID
    info=algod_client.account_info(Adress)
    
    return {"Adress":info}

@app.get("/account")
def create_account():                                   #Create a function that creates an account
    private_key, address = account.generate_account()
    passphrase = mnemonic.from_private_key(private_key)
    
    return {"address":address,"passphrase":passphrase}


@app.get("/account/{account}/balance")
def get_assets(Adress:str,asset_id:int):                                  
    info=algod_client.account_info(Adress)
    if asset_id==0:
        balance=algod_client.account_info(Adress)["amount"]
        return {"balance":balance,"asset-id":0,"asset_name":"microAlgos"}

    for asset in info["assets"]:
        if asset["asset-id"]==asset_id:
            asset_name=indexer_client.search_assets(asset_id=asset_id)["assets"][0]["params"]["name"]

            return {"balance":asset["amount"],"asset-id":asset["asset-id"],"asset_name":asset_name}
    try:
        asset_name=indexer_client.search_assets(asset_id=asset_id)["assets"][0]["params"]["name"]
    except:
        return {"ERROR":"Asset not found"}
    return {"balance":0,"asset-id":asset_id,"asset_name":asset_name}
    

@app.post("/transaction")
def create_transaction(transaction:Transaction):
    params = algod_client.suggested_params()
    unsigned_txn = PaymentTxn(transaction.sender_adress, params, transaction.receiver_adress, transaction.amount, None, transaction.note.encode()) #Create an unsigned transaction
    
    if transaction.amount < 100000:                      #check that the volume of transferred funds is greater than the minimum
        return {"amount":"amount less than the minimum"}
    try:
        signed_txn = unsigned_txn.sign(mnemonic.to_private_key(transaction.passphrase)) #trying to sign a transaction
    
    except WrongChecksumError:
        return {"passphrase":"Checksum error"}
    
    except ValueError:
        return {"passphrase":"unknown word in the passphrase"}
    
    except WrongMnemonicLengthError:
        return {"passphrase":"Incorrect size of the passphrase"}
    
    transaction_id = algod_client.send_transaction(signed_txn) #send the signed transaction to the network
    
    return transaction_id 

@app.get("/transaction/{transaction_ID}")
def get_transaction_by_ID(transaction_ID:str):         #Create a function that returns information about the transaction by ID
    return indexer_client.transaction(transaction_ID)

@app.get("/transactions/{account}")
def get_account_transactions(account:str, start_timestamp: Optional[str] = None , end_timestamp: Optional[str] = None , asset_id: Optional[int] = None):                          #Create a function that returns all transactions related to the account
    return indexer_client.search_transactions_by_address(account,start_time=start_timestamp,end_time=end_timestamp,asset_id=asset_id)

@app.post("/asset")
def create_asset(asset:Asset):
    params = algod_client.suggested_params()
    unsigned_txn=AssetConfigTxn(sp=params,                                  #create an unsigned transaction to add a new asset
                                sender=asset.sender,
                                asset_name=asset.asset_name,
                                unit_name=asset.unit,
                                total=asset.total,
                                decimals=asset.decimals,
                                default_frozen=asset.default_frozen,
                                url=asset.url,
                                manager=asset.manager,
                                reserve=asset.reserve,
                                freeze=asset.freeze,
                                clawback=asset.clawback,
                                strict_empty_address_check=False)
  
    try:
        signed_txn = unsigned_txn.sign(mnemonic.to_private_key(asset.passphrase)) #trying to sign a transaction
    
    except WrongChecksumError:
        return {"passphrase":"Checksum error"}
    
    except ValueError:
        return {"passphrase":"unknown word in the passphrase"}
    
    transaction_id = algod_client.send_transaction(signed_txn) #send the signed transaction to the network
    return transaction_id

@app.get("/assets")
def get_assets():                                   #Create a function that returns all existing assets
    return indexer_client.search_assets() 

@app.get("/assets/{asset_id}/transactions")
def get_assets(asset_id:int ,start_timestamp: Optional[str] = None , end_timestamp: Optional[str] = None):                                 
    return indexer_client.search_asset_transactions(asset_id , start_time = start_timestamp , end_time = end_timestamp) 

