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
    # doc['Borrower']

    # check if the commenter is the borrower
    if author != doc['Borrower']:
        message = f"Hi {author}, \nThis loan request was not made by you. It was made by [{doc['Borrower']}](/u/{doc['Borrower']}). Please check the post again."
        comment.reply(message)
        return
    # check if the loan is already repaid
    if doc['Repaid'] == True:
        message = f"Hi {author}, \nThis loan has already been repaid by [{doc['Lender']}](/u/{doc['Lender']}). Please check the post again."
        comment.reply(message)
        return
    # check if the 'given' field is true
    if doc['Given'] == False:
        message = f"Hi {author}, \nThis loan has not been lended yet. Please check the post again."
        comment.reply(message)
        return
    # check if amount is equal to amount requested
    if amount != doc['Amount Requested']:
        message = f"Hi {author}, \nThe amount you are trying to repay is not equal to the amount requested. Requested amount is {doc['Amount Requested']}. Please check the post again."
        comment.reply(message)
        return
    # if all the above conditions are false, update the repaid to true, add transaction ID and Date Repaid to database
    newvalues = {"$set": {"Repaid": True, "Transaction ID": transaction_id,
                          "Date Paid Back": datetime.datetime.now()}}
    message = f"Hi {author}, your loan of {doc['Amount Requested']} from [{doc['Lender']}](/u/{doc['Lender']}) has been marked repaid successfully. To confirm [{doc['Lender']}](/u/{doc['Lender']}) must reply with the following:" \
        f"""
            \n\n !paid {doc['Amount Given']}""" \
        f"\n\n**Transaction ID:** {transaction_id} **Date Repaid:** {datetime.datetime.now()}"
    self.collection.update_one(myquery, newvalues)
    comment.reply(message)
