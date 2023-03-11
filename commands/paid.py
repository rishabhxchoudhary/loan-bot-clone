# Sample Input - (comment)
# comment.body = "$confirm /u/chiefwinamac 10" 
'''
/u/chiefwinamac indicated /u/Sad-Quit-303 repaid him 10.00 USD.

These were the affected loans before this transaction
'''

def paid(self, comment):
        comment_amount = int(comment.body.split()[1])
        author = comment.author
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}

        doc = self.collection.find_one(myquery)

        if author != doc['Lender']:
            message = f"Hi {author}, \nThis loan repayment was not done to you. It was done to the original lender - [{doc['Lender']}](/u/{doc['Lender']}). Please check the post again."
            comment.reply(message)
            return
        if doc['Repaid'] == False:
            message = f"Hi {author}, \nThis loan has not been repaid by [{doc['Borrower']}](/u/{doc['Borrower']}). Please wait for the borrower to repay the loan."
            comment.reply(message)
            return
        if comment_amount != doc['Amount Given']:
            message = f"Hi {author}, \nThe amount you are trying to confirm is not equal to the amount given. Given amount is {doc['Amount Given']}. Please check the amount again."
            comment.reply(message)
            return
        newvalues = {"$set": {"Amount Repaid": comment_amount}}
        message = f"Hi {author}, your loan of {doc['Amount Given']} to [{doc['Borrower']}](/u/{doc['Borrower']}) has been confirmed successfully. For any further queries, please contact the moderators."
        self.collection.update_one(myquery, newvalues)
        comment.reply(message)
        return 