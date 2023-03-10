# Sample Input - (comment)
# comment.body = "$loan 10"
#amount requested check


# Sample output

import pymongo
import re
#mongo_uri="mongodb+srv://root:root@cluster.if4vaf9.mongodb.net/?retryWrites=true&w=majority"
#mongo_dbname="reddit"
#mongo_collection="transactions"
#collection = pymongo.MongoClient(mongo_uri)[mongo_dbname][mongo_collection]

def loan(self,comment):

        print("loan")
        post = comment.submission
        post_url = post.url

        #get the loan details from database with 'Orignal Thread' equal to post_url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find(myquery)

        #get comment details
        loan_command = comment.body.split()[0]    #$loan
        loan_amount_given = int(comment.body.split()[1])  #10
        loan_amount_max_asked = int(re.search(r'\((.*?)\)',comment.submission.title).group(1))
        
        lender_name = comment.author.name 
        borrower_name = comment.submission.author
        paid_with_id  = "XXXXX"

        if loan_amount_given<=loan_amount_max_asked and loan_amount_given>0:
            global lended #BOOL CHECK
            lended = True

            highlighted_text_1 = "!confirm {} {} USD".format(lender_name, loan_amount_given)
            highlighted_text_2 = "!paid_with_id {} {} USD".format(paid_with_id, loan_amount_given)
            
            
            # Construct the message using f-strings
            message = f"Noted! I will remember that [{lender_name}](/u/{lender_name}) lent {loan_amount_given} USD to [{borrower_name}](/u/{borrower_name})\n\n" \
            f"The format of the confirm command will be:\n"\
            f"""
            {highlighted_text_1}""" \
            f"\n\nIf you wish to mark this loan repaid later, you can use:\n"\
            f"""
            {highlighted_text_2}""" \
            f"\n\n  "\
            f"\n\nThis does NOT verify that [{lender_name}](/u/{lender_name}) actually lent anything to [{borrower_name}](/u/{borrower_name});\n\n " \
            f"[{borrower_name}](/u/{borrower_name}) should confirm here or nearby that the money was sent" \
            f"\n\n**If the loan transaction did not work out and needs to be refunded then the lender should" \
            f"reply to this comment with 'Refunded' and moderators will be automatically notified**"
            
            comment.reply(message)
            myquery = {'Orignal Thread': post_url}
            newvalues = { "$set": { "Lender":lender_name, "Amount Given":loan_amount_given } }
            self.collection.update_one(myquery, newvalues)


        else:
              message = f"Maximum Amount you can Lend is {loan_amount_max_asked} $"
              comment.reply(message)




'''
Noted! I will remember that /u/chiefwinamac lent 10.00 USD to /u/Sad-Quit-303!

The format of the confirm command will be:

$confirm /u/chiefwinamac 10.00 USD

If you wish to mark this loan repaid later, you can use:

$paid_with_id 141089 10.00 USD

This does NOT verify that /u/chiefwinamac actually lent anything to /u/Sad-Quit-303; /u/Sad-Quit-303 should confirm here or nearby that the money was sent

If the loan transaction did not work out and needs to be refunded then the lender should reply to this comment with 'Refunded' and moderators will be automatically notified
'''