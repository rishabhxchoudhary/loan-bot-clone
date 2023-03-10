# Sample Input - (comment)
# comment.body = "$confirm /u/chiefwinamac 10"

# Sample output
import pymongo
import re
import datetime

#mongo_uri="mongodb+srv://root:root@cluster.if4vaf9.mongodb.net/?retryWrites=true&w=majority"
#mongo_dbname="reddit"
#mongo_collection="transactions"
#collection = pymongo.MongoClient(mongo_uri)[mongo_dbname][mongo_collection]
#lended = True

def confirm(self,comment):

        post = comment.submission
        post_url = post.url
        #get the loan details from database with 'Orignal Thread' equal to post_url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)

        #get comment details
        comment_lender_name = comment.body.split()[1]
        borrower_name = comment.submission.author
        comment_amount_received = comment.body.split()[2]
        #get database details
        DB_records_lender_name = str(doc['Lender'])
        DB_records_amount_proposed = str(doc['Amount Given'])
        loan_id  = "xxxxx"
        #lended defined globaly

        if lended==True and comment_lender_name==DB_records_lender_name and comment_amount_received==DB_records_amount_proposed:

            print("inside confirm")
            message = f"[{borrower_name}](/u/{borrower_name}) has just confirmed that [{comment_lender_name}](/u/{comment_lender_name}) gave him/her {comment_amount_received} USD. (Reference amount: ???? USD). We matched this confirmation with this [loan]({post_url}) (id={loan_id}).\n\n" \
            f"___________________________________________________"\
            f"\n\nThe purpose of responding to !confirm is to ensure the comment doesn't get edited.\n"            
            comment.reply(message)

            myquery = {'Orignal Thread': post_url}
            newvalues = { "$set": { "Given":True, "Date Given": datetime.datetime.now()} }
            self.collection.update_one(myquery, newvalues)

        else:
              message = f"Cannot Confirm\n\n"\
                 f"that **{comment_lender_name}** has given them amount of **{comment_amount_received}** $ to **{borrower_name}**"
              comment.reply(message)

'''
/u/Sad-Quit-303 has just confirmed that /u/chiefwinamac gave him/her 10.00 USD. 
(Reference amount: 10.00 USD). We matched this confirmation with this loan (id=141089).
'''
