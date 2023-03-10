"""
Function Name: confirm()

**Description**:
    This function processes loan confirmation requests made by borrowers on Reddit. It verifies the lender's name and the loan amount requested by the borrower against the information stored in the database. If the lender's name and the loan amount match, it updates the database to mark the loan as confirmed.

**Sample Input**:
    The input to this function is a comment on Reddit containing the confirmation request. For example: !confirm lender_name 10 (where lender_name is the name of the lender and 10 is the loan amount).

**Logic**:
    1. Verify that the "lended" variable is True. This ensures that the confirm() function can only be run after the loan() function has been called.
    2. Check that the lender's name in the comment matches the lender's name stored in the database. This helps confirm that the lender's name is associated with the borrower's name in the database.
    3. Check that the loan amount confirmed by the borrower (as written in the comment) matches the loan amount proposed by the lender and stored in the database. This helps ensure that the borrower only confirms the amount that has been sent by the lender (as saved in the database when the lender called the !loan command).
    4. Update the "given" column in the database to True and add the date on which the loan was confirmed.
    5. Consider implementing a loan ID and reference amount in the database for better tracking of loans and references to specific loan transactions.

**Edge Cases**:
    - If the "lended" variable is False, the function will not update the database and will return an error message.
    - If the lender's name or the loan amount confirmed by the borrower do not match the information stored in the database, the function will not update the database and will return an error message.

**Fraud Case Analysis**:
    - A potential fraud case is when the lender gives a small amount of money, but writes a large amount in the !loan command. For example, if the lender (Rishab) gives $1 in the bank but writes !loan 100 in the comment (this $100 is saved in the database), and the borrower (Paras, who is Rishab's friend) also writes !confirm Rishab 100, even though it is a $1 transaction. In this case, both Rishab and Paras have a good history of lending and paying more money ($100) in less time. They can easily manipulate and polish their history to appear as reliable lenders and borrowers, which can be harmful to other users. To prevent such fraud cases, it's important to implement rigorous verification checks and continuously monitor the lending and borrowing activity on the platform.

**Suggestions**:
    - Adding a loan ID and reference amount in the database can help with better tracking of loans and reference to specific loan transactions. This can be useful for both the borrowers and lenders and can help avoid fraud and disputes.

"""

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

