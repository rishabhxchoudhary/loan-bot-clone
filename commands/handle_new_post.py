# Comment the history of the creator in comments.
# Make a function to get history of the creator and return final message as a string.

import pymongo
from create_table_from_list import create_table_from_list
import re

mongo_uri="mongodb+srv://root:root@cluster.if4vaf9.mongodb.net/?retryWrites=true&w=majority"
mongo_dbname="reddit"
mongo_collection="transactions"
collection = pymongo.MongoClient(mongo_uri)[mongo_dbname][mongo_collection]

def get_info(s):
    result = re.findall('\(.*?\)', s)
    return result

def handle_new_post(user_id):
    o = f'Here is information on {user_id}\n\n'
    myquery = {'requester': user_id}
    requester_doc = collection.find(myquery)
    myquery = {'lender': user_id}
    lender_doc = collection.find(myquery)
    num_requests = len(list(requester_doc))
    num_lender = len(list(lender_doc))
    count_request_completed = 0
    for requester in requester_doc:
        if( requester['paid']==True and requester['payment_received']==True and requester['returned']==True and requester['returned_received']==True):
            count_request_completed+=1
    num_rows = num_requests+num_lender
    if num_rows==0:
        l = [ ["Lender","Borrower","Amount Given","Amount Repaid","Orignal Thread","Date Given","Date Paid Back"] ]
        o+=create_table_from_list(l)
        return o
    if num_rows<=4:
        l = [ ["Borrower","Lender","Amount Given","Amount Repaid","Orignal Thread","Date Given","Date Paid Back"] ]
        for i in requester_doc:
            row = []
            row.append(i["Borrower"])
            row.append(i["Lender"])
            row.append(i["Amount Given"])
            row.append(i["Amount Repaid"])
            row.append(i["Orignal Thread"])
            row.append(i["Date Paid Back"])
            l.append(row)
        for i in lender_doc:
            row = []
            row.append(i["Borrower"])
            row.append(i["Lender"])
            row.append(i["Amount Given"])
            row.append(i["Amount Repaid"])
            row.append(i["Orignal Thread"])
            row.append(i["Date Paid Back"])
            l.append(row)
        o+=create_table_from_list(l)
        return o
    else:
        pass


