# Sample Input - (comment)
# comment.body = "$loan 10"

# Sample output
import pymongo
from create_table_from_list import create_table_from_list
import re

mongo_uri="mongodb+srv://root:root@cluster.if4vaf9.mongodb.net/?retryWrites=true&w=majority"
mongo_dbname="reddit"
mongo_collection="transactions"
collection = pymongo.MongoClient(mongo_uri)[mongo_dbname][mongo_collection]

def add_lender_record(comment):
        data = {'id': comment.id,
                'borrower': "",
                'lender': comment.author.name,
                'Amount Given': 0,
                'Amount Repaid': 0,
                'Original Thread':"",
                'Date Given': "",
                'Date Paid Back': "",
                }
        collection.insert_one(data)
        #message = f"You request has been opened with ID : {comment.id}"
        #comment.reply(message)


def loan(comment):
        #check for previous lender records
        id_lender = comment.body.split()[1]
        myquery = {'id': id}
        doc = collection.find_one(myquery)
        if doc["Lender"] == comment.author.name:
             #Record already exists
             pass
        else:
             add_lender_record(comment)

   
        comment_body_command = comment.body.split()[0]    #$loan
        loan_amount = comment.body.split()[1]  #10
        lender_name = comment.author.name     # "/u/chiefwinamac"
        Borrower_name = "/u/Sad-Quit-303"
        paid_with_id  = "141089"

        if comment_body_command == "$loan":
            message = f"""Noted! I will remember that {lender_name} lent {loan_amount} USD to {Borrower_name}

            The format of the confirm command will be:

            $confirm {lender_name} {loan_amount} USD

            If you wish to mark this loan repaid later, you can use:

            $paid_with_id {paid_with_id} {loan_amount} USD

            This does NOT verify that {lender_name} actually lent anything to {Borrower_name}; {Borrower_name} should confirm here or nearby that the money was sent

            If the loan transaction did not work out and needs to be refunded then the lender should reply to this comment with 'Refunded' and moderators will be automatically notified

            """
            comment.reply(message)
        else :
              #other commands
              #error/typo
              pass



'''
Noted! I will remember that /u/chiefwinamac lent 10.00 USD to /u/Sad-Quit-303!

The format of the confirm command will be:

$confirm /u/chiefwinamac 10.00 USD

If you wish to mark this loan repaid later, you can use:

$paid_with_id 141089 10.00 USD

This does NOT verify that /u/chiefwinamac actually lent anything to /u/Sad-Quit-303; /u/Sad-Quit-303 should confirm here or nearby that the money was sent

If the loan transaction did not work out and needs to be refunded then the lender should reply to this comment with 'Refunded' and moderators will be automatically notified
'''
