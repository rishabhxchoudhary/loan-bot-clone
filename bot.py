import praw
import pymongo
import credentials
import threading
import re
import datetime
import random
import json

def create_table_from_list(l):
    final_string = ""
    for i in range(len(l)):
        row = "|"
        for j in range(len(l[i])):
            row += str(l[i][j])+"|"
        row += '\n'
        if i == 0:
            row += ":--|"*(j+1)
            row += '\n'
        final_string += row
    return final_string

# UTC - DD MM YYYY

# Transactions 
# {
#     "Lender": "Name",
#     "Amount Given": 2432,
#     "Amount Repaid": 0,
#     "Given?": False,
#     "ID": 12345,
#     "UNPAID?":"",
#     "Date Given": None,
#     "Date Paid Back" : None

# }


class RedditBot:
    def __init__(self, client_id, client_secret, username, password, user_agent, target_subreddit):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        self.subreddit = self.reddit.subreddit(target_subreddit)
        self.collection = pymongo.MongoClient(credentials.mongo_uri)[
            credentials.mongo_dbname][credentials.mongo_collection]
        self.post_stream = self.subreddit.stream.submissions()
        self.comment_stream = self.subreddit.stream.comments()
        self.commands = {
            'help': self.help_command,
            'loan': self.loan,
            'paid\_with\_id': self.paid_with_id,
            'paid': self.paid,
            'confirm': self.confirm,
            'check': self.check
        }

    def handle_new_post(self, post):
        print(f'New post: {post.title}')
        if post.title.startswith("[REQ]"):
            doc = {
                "Borrower": str(post.author),
                "Amount Requested": int(re.search(r'\((.*?)\)', post.title).group(1)),
                "Amount Given": 0,
                "Amount Repaid": 0,
                "Orignal Thread": post.url,
                "Transactions" : {},
            }
            amt = int(re.search(r'\((.*?)\)', post.title).group(1))
            self.collection.insert_one(doc)
            o = f'Here is information on {str(post.author)}\n\n'
            l = [["Borrower", "Lender", "Amount Requested", "Amount Given", "Given",
                  "Amount Repaid", "Repaid", "Orignal Thread", "Date Given", "Date Paid Back "]]
            myquery = {'Borrower': str(post.author)}
            requester_doc = self.collection.find(myquery)
            for i in requester_doc:
                row = []
                for j in l[0]:
                    try:
                        row.append(i[j])
                    except Exception as e:
                        print(e)
                        row.append(None)
                l.append(row)
            myquery = {'Lender': str(post.author)}
            lender_doc = self.collection.find(myquery)
            for i in lender_doc:
                row = []
                for j in l[0]:
                    try:
                        row.append(i[j])
                    except Exception as e:
                        print(e)
                        row.append(None)
                l.append(row)
            o += create_table_from_list(l)
            o += f'''\n
                Command to loan should be $loan {str(amt)}
                \n
            '''
            post.reply(o)

    def loan(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        arr = doc["Transactions"]
        print(arr)
        loan_amount_given = float(comment.body.split()[1])
        amount_give_till_now = float(doc["Amount Given"])
        loan_amount_max_asked = int(
            re.search(r'\((.*?)\)', comment.submission.title).group(1))
        lender_name = comment.author.name
        borrower_name = comment.submission.author
        paid_with_id = str(random.randint(10000,99999))
        if loan_amount_max_asked-amount_give_till_now>=loan_amount_given:
            new_doc = {
                    "Lender": str(comment.author),
                    "Amount Given": loan_amount_given,
                    "Amount Repaid": 0,
                    "Given?": False,
                    "ID": paid_with_id,
                    "UNPAID?":"",
                    "Date Given": datetime.datetime.now(),
                    "Date Paid Back" : None
                }
            arr[paid_with_id] = new_doc
            newvalues = {"$set": {"Transactions": arr}}
            self.collection.update_one(myquery, newvalues)
            highlighted_text_1 = "$confirm {} {} USD".format(paid_with_id, loan_amount_given)
            highlighted_text_2 = "$paid_with_id {} {} USD".format(paid_with_id, loan_amount_given)
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
        else:
            message = f"{comment.author} \n Maximum Amount you can Lend is {loan_amount_max_asked-amount_give_till_now} $"
            comment.reply(message)

    # Given - True
    def confirm(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        comment_lender_name = comment.body.split()[1]
        comment_lender_id = comment.body.split()[2]
        
        borrower_name = comment.submission.author
        comment_amount_received = comment.body.split()[2]
        DB_records_lender_name = str(doc['transactions']['id']['Lender'])
        DB_records_amount_proposed = str(doc['Amount Given'])
        loan_id = "xxxxx"
        if  comment_lender_name == DB_records_lender_name and comment_amount_received == DB_records_amount_proposed:
            print("inside confirm")
            message = f"[{borrower_name}](/u/{borrower_name}) has just confirmed that [{comment_lender_name}](/u/{comment_lender_name}) gave him/her {comment_amount_received} USD. (Reference amount: ???? USD). We matched this confirmation with this [loan]({post_url}) (id={loan_id}).\n\n" \
                f"___________________________________________________"\
                f"\n\nThe purpose of responding to !confirm is to ensure the comment doesn't get edited.\n"
            comment.reply(message)
            myquery = {'Orignal Thread': post_url}
            newvalues = {"$set": {"Given": True,
                                  "Date Given": datetime.datetime.now()}}
            self.collection.update_one(myquery, newvalues)
        else:
            message = f"Cannot Confirm\n\n"\
                f"that **{comment_lender_name}** has given them amount of **{comment_amount_received}** $ to **{borrower_name}**"
            comment.reply(message)


    #  Traverse till found id, add to amount REPAID.
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
                              "Date Repaid": datetime.datetime.now()}}
        message = f"Hi {author}, your loan of {doc['Amount Requested']} from [{doc['Lender']}](/u/{doc['Lender']}) has been marked repaid successfully. To confirm [{doc['Lender']}](/u/{doc['Lender']}) must reply with the following:" \
            f"""
            \n\n !paid {doc['Amount Given']}""" \
            f"\n\n**Transaction ID:** {transaction_id} **Date Repaid:** {datetime.datetime.now()}"
        self.collection.update_one(myquery, newvalues)
        comment.reply(message)

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

    def check(self, comment):
        user_id = comment.body.split()[1]
        o = f'Here is information on {user_id}\n\n'
        l = [["Borrower", "Lender", "Amount Requested", "Amount Given", "Given",
              "Amount Repaid", "Repaid", "Orignal Thread", "Date Given", "Date Repaid"]]
        myquery = {'Borrower': str(user_id)}
        requester_doc = self.collection.find(myquery)
        for i in requester_doc:
            row = []
            for j in l[0]:
                try:
                    row.append(i[j])
                except Exception as e:
                    print(e)
                    row.append(None)
            l.append(row)
        myquery = {'Lender': str(user_id)}
        lender_doc = self.collection.find(myquery)
        for i in lender_doc:
            row = []
            for j in l[0]:
                try:
                    row.append(i[j])
                except Exception as e:
                    print(e)
            l.append(row)
        o += create_table_from_list(l)
        comment.reply(o)

    def help_command(self, comment):
        message = 'Here are the available commands: '
        for command in self.commands.keys():
            message += f'!{command}, '
        message = message[:-2]
        comment.reply(message)

    def handle_new_comment(self, comment):
        print(f'New Comment:', comment.body)
        if comment.body.strip().startswith('$'):
            command = comment.body.split()[0].lower()[1:]
            if command in self.commands:
                self.commands[command](comment)
            else:
                message = "Invalid Command!"
                comment.reply(message)

    def listen_for_comments(self):
        print("Listening for comments")
        for comment in self.subreddit.stream.comments(skip_existing=True):
            self.handle_new_comment(comment)

    def listen_for_posts(self):
        print("Listening for posts")
        for post in self.subreddit.stream.submissions(skip_existing=True):
            self.handle_new_post(post)

    def start(self):
        print("Bot is ready")
        thread1 = threading.Thread(target=self.listen_for_comments)
        thread2 = threading.Thread(target=self.listen_for_posts)
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()


if __name__ == "__main__":
    bot = RedditBot(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        user_agent=credentials.user_agent,
        username=credentials.username,
        password=credentials.password,
        target_subreddit=credentials.subreddit_name
    )
    bot.start()
