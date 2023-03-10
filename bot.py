import praw
import pymongo
import credentials
import threading
import re
import datetime

def create_table_from_list(l):
    final_string=""
    for i in range(len(l)):
        row="|"
        for j in range(len(l[i])):
            row+=str(l[i][j])+"|"
        row+='\n'
        if i==0:
            row+=":--|"*(j+1)
            row+='\n'
        final_string+=row
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
            'greet': self.greet_command,
            'help': self.help_command,
            'request': self.request,
            'accept': self.accept,
            'paid': self.paid_command,
            'returned': self.returned,
            'returnedAccepted': self.returned_accepted,
            'history': self.history,
            'paid\_with\_id': self.paid_with_id
        }
    
    def paid_with_id(self,comment):
        author = comment.author
        post = comment.submission
        post_url = post.url
        comment_list = comment.body.split()
        transaction_id = comment_list[1]
        amount = int(comment_list[2])
        myquery = {'Orignal Thread': post_url}
        doc = self.collection.find_one(myquery)
        if author != doc['Borrower']:
            message = f"This was detected as the correct format for paying a loan with a given id, but you do not control this loan. Borrower username is {doc['Borrower']}. Please check the post again."
            comment.reply(message)
            return
        if doc['Repaid'] == True:
            message = f"This was detected as the correct format for paying a loan with a given id, but this loan is already repaid. Please check the post again."
            comment.reply(message)
            return
        if doc['Given'] == False:
            message = f"This was detected as the correct format for paying a loan with a given id, but this loan is not marked as given. Please check the post again."
            comment.reply(message)
            return
        if amount != doc['Amount Requested']:
            message = f"This was detected as the correct format for paying a loan with a given id, but the amount is not equal to the amount requested. Please check the post again."
            comment.reply(message)
            return
        newvalues = {"$set": {"Repaid": True, "Transaction ID": transaction_id, "Date Repaid": datetime.datetime.now()}}
        self.collection.update_one(myquery, newvalues)
        message = f"This was detected as the correct format for paying a loan with a given id. The loan has been marked as repaid. Reply with !paid to confirm."
        comment.reply(message)

    def accept(self, comment):
        id = comment.body.split()[1]
        myquery = {'id': id}
        doc = self.collection.find_one(myquery)
        if doc["requester"] == comment.author.name:
            newvalues = {"$set": {"payment_received": True}}
            self.collection.update_one(myquery, newvalues)
            message = f"Payment has been accepted for id = {id}"
            comment.reply(message)
        else:
            message = f"Only the requester can make an accept request!"
            comment.reply(message)

    def history(self, comment):
        user_id = comment.body.split()[1]
        myquery = {'requester': user_id}
        requester_doc = self.collection.find(myquery)

        myquery = {'lender': user_id}
        lender_doc = self.collection.find(myquery)

        count_request_completed = 0
        num_requests = len(list(requester_doc))
        num_lender = len(list(lender_doc))

        for requester in requester_doc:
            if( requester['paid']==True and requester['payment_received']==True and requester['returned']==True and requester['returned_received']==True):
                count_request_completed+=1
        
        message=f'num_requests:{num_requests},\nnum_lender:{num_lender}, \ncount_request_completed:{count_request_completed}'
        comment.reply(message)


    def returned(self, comment):
        id = comment.body.split()[1]
        myquery = {'id': id}
        doc = self.collection.find_one(myquery)
        if doc["requester"] == comment.author.name:
            newvalues = {"$set": {"returned": True}}
            self.collection.update_one(myquery, newvalues)
            message = f"Payment has been accepted for id = {id}"
            comment.reply(message)
        else:
            message = f"Only the requester can make a returned request!"
            comment.reply(message)

    def returned_accepted(self, comment):
        id = comment.body.split()[1]
        myquery = {'id': id}
        doc = self.collection.find_one(myquery)
        if doc["lender"] == comment.author.name:
            newvalues = {"$set": {"returned_accepted": True}}
            self.collection.update_one(myquery, newvalues)
            message = f"Payment has been returned for id = {id}. Transaction has been closed now."
            comment.reply(message)
        else:
            message = f"Only the lender can make an accepted return request!"
            comment.reply(message)

    def paid_command(self, comment):
        print("Payment processing")
        object_id = comment.body.split()[1]
        lender_name = comment.author.name
        transaction = self.collection.find_one({'id': object_id})
        if transaction is None:
            comment.reply(f'Error: transaction with id {object_id} not found')
            return
        requester = transaction['requester']
        message = f'Hi, {lender_name}! You have paid {requester} for their request. {requester}please confirm by replying to this comment with !accept {object_id}'
        self.collection.update_one({'id': object_id}, {'$set': {'paid': True}})
        self.collection.update_one(
            {'id': object_id}, {'$set': {'lender': lender_name}})
        comment.reply(message)

    def request(self, comment):
        data = {'id': comment.id,
                'requester': comment.author.name,
                'lender': "",
                'paid': False,
                'payment_received': False,
                'returned': False,
                'returned_received': False,
                }
        self.collection.insert_one(data)
        message = f"You request has been opened with ID : {comment.id}"
        comment.reply(message)

    def greet_command(self, comment):
        message = f'Hello, {comment.author.name}! How are you today?'
        comment.reply(message)

    def help_command(self, comment):
        message = 'Here are the available commands: '
        for command in self.commands.keys():
            message += f'!{command}, '
        message = message[:-2]
        comment.reply(message)

    def handle_new_comment(self, comment):
        print(f'New Comment:', comment.body)
        if comment.body.strip().startswith('!'):
            command = comment.body.split()[0].lower()[1:]
            if command in self.commands:
                self.commands[command](comment)
            else:
                message = "Invalid Command!"
                comment.reply(message)

    def handle_new_post(self, post):
        print(f'New post: {post.title}')
        if post.title.startswith("[REQ]"):
            doc = {
                "Borrower" : str(post.author),
                "Lender": "",
                "Amount Requested": int(re.search(r'\((.*?)\)',post.title).group(1)),
                "Amount Given": 0,
                "Given": False,
                "Amount Repaid" : 0,
                "Repaid":False,
                "Orignal Thread": post.url,
                "Date Given": None,
                "Date Repaid": None
            }
            amt = int(re.search(r'\((.*?)\)',post.title).group(1))
            self.collection.insert_one(doc)
            o = f'Here is information on {str(post.author)}\n\n'
            l = [ ["Borrower","Lender","Amount Requested","Amount Given","Given","Amount Repaid","Repaid","Orignal Thread","Date Given","Date Repaid"] ]
            myquery = {'Borrower': str(post.author)}
            requester_doc = self.collection.find(myquery)
            for i in requester_doc:
                    row = []
                    for j in l[0]:
                        row.append(i[j])
                    l.append(row)
            myquery = {'Lender': str(post.author)}
            lender_doc = self.collection.find(myquery)
            for i in lender_doc:
                    row = []
                    for j in l[0]:
                        row.append(i[j])
                    l.append(row)
            o += create_table_from_list(l)
            o+=f'''\n
                Command to loan should be $loan {str(amt)}
                \n
            '''
            post.reply(o)

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
