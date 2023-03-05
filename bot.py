import praw
import pymongo
import credentials
import threading

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
        self.post_collection = pymongo.MongoClient(credentials.mongo_uri)[
            credentials.mongo_dbname][credentials.mongo_post_collection]
        self.comment_collection = pymongo.MongoClient(credentials.mongo_uri)[
            credentials.mongo_dbname][credentials.mongo_comment_collection]
        self.post_stream = self.subreddit.stream.submissions()
        self.comment_stream = self.subreddit.stream.comments()
        self.commands = {
            'greet': self.greet_command,
            'help': self.help_command,
        }
    
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
        if comment.body.startswith('!'):
            command = comment.body.split()[0].lower()[1:]
            if command in self.commands:
                data = {'id': comment.id,
                        'author': comment.author.name,
                        'body': comment.body,
                        'subreddit': comment.subreddit.display_name,
                        'created_utc': comment.created_utc
                    }
                self.comment_collection.insert_one(data)
                self.commands[command](comment)

    def handle_new_post(self, post):
        print(f'New post: {post.title}')
        data = {
            'title': post.title,
            'author': post.author.name,
            'created_utc': post.created_utc,
            'permalink': post.permalink,
            'url': post.url,
        }
        self.post_collection.insert_one(data)

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
