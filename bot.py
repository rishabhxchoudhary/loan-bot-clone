import praw
import pymongo
import credentials
import threading
import re
import datetime
import random


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
            'repaid\_with\_id': self.repaid_with_id,
            'repaid\_confirm': self.repaid_confirm,
            'confirm': self.confirm,
            'check': self.check
        }

    def handle_new_post(self, post):
        print(f'New post: {post.title}')
        if post.title.startswith("[REQ]"):
            doc = {
                "Borrower": str(post.author),
                "Amount Requested": float(re.search(r'\((.*?)\)', post.title).group(1)),
                "Amount Given": 0,
                "Amount Repaid": 0,
                "Orignal Thread": post.url,
                "Transactions": {},
            }
            amt = float(re.search(r'\((.*?)\)', post.title).group(1))
            self.collection.insert_one(doc)
            o = f'Here is information on {str(post.author)}\n\n'
            l = [["Borrower", "Lender", "Amount Given", "Amount Repaid",
                  "Orignal Thread", "Date Given", "Date Paid Back "]]
            myquery = {'Borrower': str(post.author)}
            requester_doc = self.collection.find(myquery)
            for i in requester_doc:
                for transaction in i["Transactions"]:
                    try:
                        row = []
                        row.append(str(post.author))
                        row.append(i["Transactions"][transaction]["Lender"])
                        row.append(i["Transactions"]
                                   [transaction]["Amount Given"])
                        row.append(i["Transactions"][transaction]
                                   ["Amount Repaid"])
                        row.append(i["Orignal Thread"])
                        row.append(i["Transactions"]
                                   [transaction]["Date Given"])
                        row.append(i["Transactions"][transaction]
                                   ["Date Paid Back"])
                        l.append(row)
                    except Exception as e:
                        print(e)
            pipeline = [
                {
                    "$match":   {"$expr": {
                        "$gt": [
                            {
                                "$size": {
                                    "$filter": {
                                        "input": {"$objectToArray": "$Transactions"},
                                        "as": "item",
                                        "cond": {
                                            "$eq": [
                                                f"{str(post.author)}",
                                                {
                                                    "$reduce": {
                                                        "input": {"$objectToArray": "$$item.v"},
                                                        "initialValue": "",
                                                        "in": {
                                                            "$cond": {
                                                                "if": {"$eq": ["Lender", "$$this.k"]},
                                                                "then": "$$this.v",
                                                                "else": "$$value"
                                                            }
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            },
                            0
                        ]
                    }
                    }
                }
            ]
            lender_doc = self.collection.aggregate(pipeline)
            for doc in lender_doc:
                for transaction in doc["Transactions"]:
                    try:
                        if doc["Transactions"][transaction]["Lender"] == str(post.author):
                            row = []
                            row.append(doc["Borrower"])
                            row.append(doc["Transactions"]
                                       [transaction]["Lender"])
                            row.append(doc["Transactions"]
                                       [transaction]["Amount Given"])
                            row.append(doc["Transactions"]
                                       [transaction]["Amount Repaid"])
                            row.append(doc["Orignal Thread"])
                            row.append(doc["Transactions"]
                                       [transaction]["Date Given"])
                            row.append(doc["Transactions"]
                                       [transaction]["Date Paid Back"])
                            l.append(row)
                    except Exception as e:
                        print(e)
            o += create_table_from_list(l)
            o += f"\nCommand to loan should be ```$loan {str(amt)}```\n"
            post.reply(o)
            
        else:
            post.mod.remove()

    def loan(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        arr = doc["Transactions"]
        loan_amount_given = float(comment.body.split()[1])
        amount_give_till_now = float(doc["Amount Given"])
        loan_amount_max_asked = float(
            re.search(r'\((.*?)\)', comment.submission.title).group(1))
        lender_name = comment.author.name
        borrower_name = comment.submission.author
        paid_with_id = str(random.randint(10000, 99999))

        if borrower_name == lender_name:
            message = f"[{borrower_name}](/u/{borrower_name})-Borrower dont have access to write this command."
            comment.reply(message)
        elif loan_amount_max_asked-amount_give_till_now >= loan_amount_given and loan_amount_given > 0:
            new_doc = {
                "Lender": str(comment.author),
                "Amount Given": loan_amount_given,
                "Amount Repaid": 0,
                "Given?": False,
                "ID": paid_with_id,
                "UNPAID?": "",
                "Date Given": datetime.datetime.now(),
                "Date Paid Back": None,
                "Completed?": False
            }

            arr[paid_with_id] = new_doc
            newvalues = {"$set": {"Transactions": arr}}
            self.collection.update_one(myquery, newvalues)

            highlighted_text_1 = "$confirm {} {} USD".format(
                paid_with_id, loan_amount_given)
            highlighted_text_2 = "$repaid_with_id {} {} USD".format(
                paid_with_id, loan_amount_given)
            message = f"Noted! I will remember that [{lender_name}](/u/{lender_name}) lent {loan_amount_given} USD to [{borrower_name}](/u/{borrower_name})\n\n" \
                f"```The unique id for this transaction is - {paid_with_id}```\n\n"\
                f"The format of the confirm command will be:\n\n"\
                f"```{highlighted_text_1}```" \
                f"\n\nIf you wish to mark this loan repaid later, you can use:\n\n"\
                f"```{highlighted_text_2}```" \
                f"\n\n  "\
                f"\n\nThis does NOT verify that [{lender_name}](/u/{lender_name}) actually lent anything to [{borrower_name}](/u/{borrower_name});\n\n " \
                f"[{borrower_name}](/u/{borrower_name}) should confirm here or nearby that the money was sent" \
                f"\n\n**If the loan transaction did not work out and needs to be refunded then the lender should" \
                f" reply to this comment with 'Refunded' and moderators will be automatically notified**"
            comment.reply(message)
        else:
            message = f"[{comment.author}](/u/{comment.author}) \n Maximum Amount you can Lend is {loan_amount_max_asked-amount_give_till_now} $"
            comment.reply(message)

    def confirm(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        existing_amt_given = doc["Amount Given"]
        amount_requested = doc["Amount Requested"]
        transactions = doc["Transactions"]
        paid_with_id = comment.body.split()[1]
        comment_amount_received = float(comment.body.split()[2])

        borrower_name = comment.submission.author
        comment_author = comment.author
        lender_name = transactions[paid_with_id]["Lender"]
        lender_actual_amount_given = float(
            transactions[paid_with_id]['Amount Given'])

        if paid_with_id in transactions:

            if borrower_name != comment_author:
                message = f"[{lender_name}](/u/{lender_name}), is not authorized to confirm this loan. Only [{borrower_name}](/u/{borrower_name}) can do this."
                comment.reply(message)
                return

            if comment_amount_received != lender_actual_amount_given:
                message = f"[{borrower_name}](/u/{borrower_name}), the loan cannot be confirmed.\n\n The Amount {comment_amount_received} $ you are confirming, doesnt match the amount what [{lender_name}](/u/{lender_name} has paid"
                comment.reply(message)
                return
            transactions[paid_with_id]["Given?"] = True
            existing_amt_given += float(comment_amount_received)

            message = f"[{borrower_name}](/u/{borrower_name}) has just confirmed that [{lender_name}](/u/{lender_name}) gave him/her {comment_amount_received} USD. (Reference amount: {amount_requested} USD). We matched this confirmation with this [loan]({post_url}) (id={paid_with_id}).\n\n" \
                f"___________________________________________________"\
                f"\n\nThe purpose of responding to $confirm is to ensure the comment doesn't get edited.\n"
            comment.reply(message)
            myquery = {'Orignal Thread': post_url}
            newvalues = {"$set": {"Transactions": transactions,
                                  "Amount Given": existing_amt_given}}
            self.collection.update_one(myquery, newvalues)
        else:
            message = f"Cannot Confirm!\n\n"\
                f"**[{lender_name}](/u/{lender_name}** has given them amount of **{comment_amount_received}** $ to **[{borrower_name}](/u/{borrower_name})**"
            comment.reply(message)

    #  Traverse till found id, add to amount REPAID.

    def repaid_with_id(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        transactions = doc["Transactions"]
        id = comment.body.split()[1]
        comment_amount_repaid = float(comment.body.split()[2])
        borrower_name = comment.submission.author
        comment_author = comment.author
        if id in transactions:
            # check if borrower name is same as comment author
            lender_name = transactions[id]["Lender"]

            if borrower_name != comment_author:
                message = f"Hi {str(comment.author)}, you are not authorized to mark this loan as repaid. Only [{borrower_name}](/u/{borrower_name}) can do this."
                comment.reply(message)
                return

            # check if loan has been marked given then wait for borrower to confirm
            if transactions[id]["Given?"] == False:
                message = f"Hi {str(comment.author)}, You have not confirmed that [{lender_name}](/u/{lender_name}) has given you the loan. Please confirm this first."
                comment.reply(message)
                return

            # check if comment_amount_repaid is same as amount given in transaction
            if comment_amount_repaid != transactions[id]["Amount Given"]:
                message = f"Hi {str(comment.author)}, the amount you have entered to mark this loan as repaid is not the same as the amount given in the transaction. Please enter the correct amount."
                comment.reply(message)
                return

            # check if transaction is completed
            if transactions[id]["Completed?"] == True:
                message = f"Hi {str(comment.author)}, this transaction is already completed."
                comment.reply(message)
                return

            # if transaction amount repaid is not zero, i.e., author has already repaid the loan but lender has not confirmed it.
            if transactions[id]["Amount Repaid"] != 0:
                message = f"Hi {str(comment.author)}, you have already repaid this loan. Please wait for [{lender_name}](/u/{lender_name}) to confirm this."
                comment.reply(message)
                return

            # update amount repaid to coment amount repaid add date paid back as current time
            transactions[id]["Amount Repaid"] += float(comment_amount_repaid)
            transactions[id]["Date Paid Back"] = datetime.datetime.now()
            newvalues = {
                "$set": {
                    "Transactions": transactions,
                }
            }
            self.collection.update_one(myquery, newvalues)
            message = f"Hi {str(comment.author)}, your loan of {comment_amount_repaid} from [{lender_name}](/u/{lender_name}) has noted successfully. To confirm [{borrower_name}](/u/{borrower_name}) must reply with the following:" \
                f"""
            \n\n```$repaid_confirm {id} {comment_amount_repaid}```""" \
            f"\n\n**Transaction ID:** {id} **Date Repaid:** {datetime.datetime.now()}"
            self.collection.update_one(myquery, newvalues)
        else:
            message = f"Transaction ID not found. Please check command again."
        comment.reply(message)

    def repaid_confirm(self, comment):
        post = comment.submission
        post_url = post.url
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        current_repaid_amount = float(doc["Amount Repaid"])
        transactions = doc["Transactions"]
        comment_author = comment.author
        comment_amount_repaid = float(comment.body.split()[2])
        borrower_name = comment.submission.author
        id = comment.body.split()[1]
        if id in transactions:
            # check if lender name is same as comment author
            lender_name = transactions[id]["Lender"]

            if lender_name != comment_author:
                message = f"Hi {str(comment.author)}, you are not authorized to mark this loan as repaid. Only [{lender_name}](/u/{lender_name}) can do this."
                comment.reply(message)
                return

            # check if loan has been marked given then wait for borrower to confirm
            if transactions[id]["Given?"] == False:
                message = f"Hi {str(comment.author)}, You have not confirmed that [{lender_name}](/u/{lender_name}) has given you the loan. Please confirm this first."
                comment.reply(message)
                return

            # check if comment_amount_repaid is same as amount given in transaction
            if comment_amount_repaid != transactions[id]["Amount Given"]:
                message = f"Hi {str(comment.author)}, the amount you have entered to confirm this loan as repaid is not the same as the amount given in the transaction. Please enter the correct amount."
                comment.reply(message)
                return

            # check if transaction is completed
            if transactions[id]["Completed?"] == True:
                message = f"Hi {str(comment.author)}, this transaction is already completed."
                comment.reply(message)
                return

            # if transaction amount repaid is zero, i.e., author has not repaid the loan.
            if transactions[id]["Amount Repaid"] == 0:
                message = f"Hi {str(comment.author)}, [{borrower_name}](/u/{borrower_name}) has not repaid this loan. Please wait for [{borrower_name}](/u/{borrower_name}) to confirm this."
                comment.reply(message)
                return

            # update completed to true and add amount repaid to current repaid amount
            transactions[id]["Completed?"] = True
            current_repaid_amount += float(comment_amount_repaid)
            newvalues = {
                "$set": {
                    "Transactions": transactions,
                    "Amount Repaid": current_repaid_amount
                }
            }

            self.collection.update_one(myquery, newvalues)
            message = f"Hi {str(comment.author)}, the loan of {comment_amount_repaid} to [{borrower_name}](/u/{borrower_name}) has been completed successfully."
            f"\n\n**Transaction ID:** {id} **Date Repaid:** {datetime.datetime.now()}"
            self.collection.update_one(myquery, newvalues)
        else:
            message = f"Transaction ID not found. Please check command again."
        comment.reply(message)

    def check(self, comment):
        user_id = comment.body.split()[1]
        o = f'Here is information on {user_id}\n\n'
        # l = [["Borrower", "Lender", "Amount Requested", "Amount Given", "Given",
        #       "Amount Repaid", "Repaid", "Orignal Thread", "Date Given", "Date Repaid"]]
        l = [["Borrower", "Lender", "Amount Given", "Amount Repaid",
              "Orignal Thread", "Date Given", "Date Paid Back "]]
        myquery = {'Borrower': str(user_id)}
        requester_doc = self.collection.find(myquery)
        for i in requester_doc:
            for transaction in i["Transactions"]:
                try:
                    row = []
                    row.append(str(user_id))
                    row.append(i["Transactions"][transaction]["Lender"])
                    row.append(i["Transactions"]
                                [transaction]["Amount Given"])
                    row.append(i["Transactions"][transaction]
                                ["Amount Repaid"])
                    row.append(i["Orignal Thread"])
                    row.append(i["Transactions"]
                                [transaction]["Date Given"])
                    row.append(i["Transactions"][transaction]
                                ["Date Paid Back"])
                    l.append(row)
                except Exception as e:
                    print(e)
        pipeline = [
            {
                "$match":   {"$expr": {
                    "$gt": [
                        {
                            "$size": {
                                "$filter": {
                                    "input": {"$objectToArray": "$Transactions"},
                                    "as": "item",
                                    "cond": {
                                        "$eq": [
                                            f"{str(user_id)}",
                                            {
                                                "$reduce": {
                                                    "input": {"$objectToArray": "$$item.v"},
                                                    "initialValue": "",
                                                    "in": {
                                                        "$cond": {
                                                            "if": {"$eq": ["Lender", "$$this.k"]},
                                                            "then": "$$this.v",
                                                            "else": "$$value"
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        0
                    ]
                }
                }
            }
        ]
        lender_doc = self.collection.aggregate(pipeline)
        for doc in lender_doc:
            for transaction in doc["Transactions"]:
                try:
                    if doc["Transactions"][transaction]["Lender"] == str(post.author):
                        row = []
                        row.append(doc["Borrower"])
                        row.append(doc["Transactions"]
                                   [transaction]["Lender"])
                        row.append(doc["Transactions"]
                                   [transaction]["Amount Given"])
                        row.append(doc["Transactions"]
                                   [transaction]["Amount Repaid"])
                        row.append(doc["Orignal Thread"])
                        row.append(doc["Transactions"]
                                   [transaction]["Date Given"])
                        row.append(doc["Transactions"]
                                   [transaction]["Date Paid Back"])
                        l.append(row)
                except Exception as e:
                    print(e)
        o += create_table_from_list(l)
        comment.reply(o)

    def help_command(self, comment):
        message = 'Here are the available commands: '
        message += ' \n\n'
        message += ' ```$check <user_id>``` - Check the status of a user. '
        message += ' \n\n'
        message += ' ```$help``` - Get help with the commands. '
        message += ' \n\n'
        message += ' ```$loan <amount>``` - Offer a loan to the author of the post. '
        message += ' \n\n'
        message += ' ```$confirm <transaction_id> <amoount>``` - Confirm a loan with the given transaction id. '
        message += ' \n\n'
        message += ' ```$repaid_with_id <transaction_id> <amount>``` - Inform that the loan has been repaid with the given transaction id. '
        message += ' \n\n'
        message += ' ```$repaid_confirm <transaction_id> <amount>``` - Confirm that the loan has been repaid with the given transaction id. '
        message += ' \n\n'
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
