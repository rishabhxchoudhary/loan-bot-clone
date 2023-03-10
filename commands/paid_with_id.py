# Sample Input - (comment)
# comment.body = "$paid_with_id 141089 10.00 USD"

'''
This was detected as the correct format for paying a loan with a given id, but you do not control this loan. Verify the following:

The loan command was processed correctly. This can be seen by using the search page

You have the loan id and money amount in the correct order. You want it to be $paid_with_id (LOAN ID) (AMOUNT TO REPAY)

You are using the correct loan id (use the search page and press "Details" to see the loan ids)

The loan is not already marked as repaid
'''

# Check reddit for exact message
# url = https://www.reddit.com/r/borrow/comments/11cunqu/req_10_wichita_ks_usa_repay_20_on_0303_paypal/

import datetime
from commands.create_table_from_list import create_table_from_list

def paid_with_id(self, comment):
    author = comment.author
    post = comment.submission
    post_url = post.url
    # break the comment into list of words
    comment_list = comment.body.split()
    transaction_id = comment_list[1]
    amount = int(comment_list[2])
    # get the loan details from database with 'Orignal Thread' equal to post_url
    myquery = {'Orignal Thread': post_url}
    doc = self.collection.find_one(myquery)

    # check if the commenter is the borrower
    if author != doc['Borrower']:
        message = f"This was detected as the correct format for paying a loan with a given id, but you do not control this loan. Borrower username is {doc['Borrower']}. Please check the post again."
        comment.reply(message)
        return
    # check if the loan is already repaid
    if doc['Repaid'] == True:
        message = f"This was detected as the correct format for paying a loan with a given id, but this loan is already repaid. Please check the post again."
        comment.reply(message)
        return
    # check if the 'given' field is true
    if doc['Given'] == False:
        message = f"This was detected as the correct format for paying a loan with a given id, but this loan is not marked as given. Please check the post again."
        comment.reply(message)
        return
    # check if amount is equal to amount requested
    if amount != doc['Amount Requested']:
        message = f"This was detected as the correct format for paying a loan with a given id, but the amount is not equal to the amount requested. Please check the post again."
        comment.reply(message)
        return
    # if all the above conditions are false, update the repaid to true, add transaction ID and Date Repaid to database
    newvalues = {"$set": {"Repaid": True, "Transaction ID": transaction_id, "Date Paid Back": datetime.datetime.now()}}
    self.collection.update_one(myquery, newvalues)
    message = f"This was detected as the correct format for paying a loan with a given id. The loan has been marked as repaid. Reply with !paid to confirm."
    comment.reply(message)
