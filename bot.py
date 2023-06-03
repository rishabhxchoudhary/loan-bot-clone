import praw
import pymongo
import certifi
import credentials
import threading
import re
import datetime
import random
from currency_converter import CurrencyConverter

c = CurrencyConverter()

currencies_supported = [
    "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF", "ISK", "NOK", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS", "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR"
]


def create_table_from_list(l):
    final_string = ""
    for i in range(len(l)):
        row = "|"
        for j in range(len(l[i])):
            row += str(l[i][j]) + "|"
        row += "\n"
        if i == 0:
            row += ":--|" * (j + 1)
            row += "\n"
        final_string += row
    return final_string


class RedditBot:
    def __init__(
        self, client_id, client_secret, username, password, user_agent, target_subreddit
    ):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )
        self.subreddit = self.reddit.subreddit(target_subreddit)
        self.collection = pymongo.MongoClient(
            credentials.mongo_uri, tlsCAFile=certifi.where()
        )[credentials.mongo_dbname][credentials.mongo_collection]
        self.post_collection = pymongo.MongoClient(
            credentials.mongo_uri, tlsCAFile=certifi.where()
        )["Posts"][credentials.mongo_collection]
        self.post_stream = self.subreddit.stream.submissions()
        self.comment_stream = self.subreddit.stream.comments()

        self.REQ_POST_REGEX = r"\[REQ\]\s\(([\d.]+)\)\s\(([^)]+)\)\s-\s\(([^)]+)\),\s\(([^)]+)\),\s\(([^)]+)\)"
        self.OFFER_POST_REGEX = r"^\[OFFER\] - \((.*?)\)$"
        self.UNPAID_POST_REGEX = (
            r"^\[UNPAID\] \((.*?)\) - \((\d+\.\d+|\d+)\) \((.*?)\)$"
        )
        self.PAID_POST_REGEX = r"^\[PAID\] \((.*?)\) - \((\d+\.\d+|\d+)\) \((.*?)\)$"
        self.LOAN_REGEX = r"\$loan\s+(\d+(\.\d+)?)\s+(\w+)"
        self.CONFIRM_REGEX = r"^\$confirm\s(\d{5})\s([-+]?\d*\.?\d+)\s(\w+)$"
        self.REPAID_REGEX = r"^\$repaid\\_with\\_id\s(\d{5})\s([-+]?\d*\.?\d+)\s(\w+)$"
        self.REPAID_CONFIRM_REGEX = r"^\$repaid\\_confirm\s(\d{5})\s([-+]?\d*\.?\d+)\s(\w+)$"
        self.commands = {
            "help": self.help_command,
            "loan": self.loan,
            "repaid\_with\_id": self.repaid_with_id,
            "repaid\_confirm": self.repaid_confirm,
            "confirm": self.confirm,
            "check": self.check,
            "unpaid": self.unpaid,
        }

    def get_user_details(self, username):
        l = [
            [
                "Borrower",
                "Lender",
                "Amount Given",
                "Currency Given",
                "Given",
                "Amount Repaid",
                "Currency Repaid",
                "Repaid",
                "Orignal Thread",
                "Date Given",
                "Date Repaid",
            ]
        ]
        o = f"Here is information on {str(username)}\n\n"
        count_borrower_completed = 0
        count_borrower_completed_amount = 0.0
        count_borrower_unpaid = 0
        amount_borrower_unpaid = 0.0
        count_borrowed_ongoing = 0
        amount_borrower_ongoing = 0.0
        count_lender_completed = 0
        amount_lender_completed = 0.0
        count_lender_unpaid = 0
        amount_lender_unpaid = 0.0
        count_lender_ongoing = 0
        amount_lender_ongoing = 0.0
        myquery = {"Borrower": str(username)}
        requester_doc = self.collection.find(myquery)
        for i in requester_doc:
            for transaction in i["Transactions"]:
                try:
                    row = []
                    row.append(str(username))
                    row.append(i["Transactions"][transaction]["Lender"])
                    row.append(i["Transactions"][transaction]["Amount Given"])
                    row.append(i["Transactions"][transaction]["Currency Given"])
                    row.append(i["Transactions"][transaction]["Given?"])
                    row.append(i["Transactions"][transaction]["Amount Repaid"])
                    row.append(i["Transactions"][transaction]
                               ["Currency Repaid"])
                    if i["Transactions"][transaction]["Completed?"] == True:
                        row.append(True)
                    else:
                        row.append(False)
                    row.append(i["Orignal Thread"])
                    row.append(i["Transactions"][transaction]["Date Given"])
                    row.append(i["Transactions"][transaction]
                               ["Date Paid Back"])
                    if i["Transactions"][transaction]["Completed?"] == True:
                        count_borrower_completed += 1

                        completed_amount = float(
                            i["Transactions"][transaction]["Amount Given"]
                        )
                        completed_currency = i["Transactions"][transaction]["Currency Given"]
                        count_borrower_completed_amount += float(
                            c.convert(completed_amount, completed_currency, "USD"))

                    elif i["Transactions"][transaction]["UNPAID?"] == True:
                        count_borrower_unpaid += 1
                        unpaid_amount = float(
                            i["Transactions"][transaction]["Amount Given"])
                        unpaid_currency = i["Transactions"][transaction]["Currency Given"]
                        amount_borrower_unpaid += float(
                            c.convert(unpaid_amount, unpaid_currency, "USD"))
                    else:
                        count_borrowed_ongoing += 1
                        ongoing_amount = float(
                            i["Transactions"][transaction]["Amount Given"])
                        ongoing_currency = i["Transactions"][transaction]["Currency Given"]
                        amount_borrower_ongoing += float(
                            c.convert(ongoing_amount, ongoing_currency, "USD"))
                    l.append(row)
                except Exception as e:
                    print(e)

        pipeline = [
            {
                "$match": {
                    "$expr": {
                        "$gt": [
                            {
                                "$size": {
                                    "$filter": {
                                        "input": {"$objectToArray": "$Transactions"},
                                        "as": "item",
                                        "cond": {
                                            "$eq": [
                                                f"{str(username)}",
                                                {
                                                    "$reduce": {
                                                        "input": {
                                                            "$objectToArray": "$$item.v"
                                                        },
                                                        "initialValue": "",
                                                        "in": {
                                                            "$cond": {
                                                                "if": {
                                                                    "$eq": [
                                                                        "Lender",
                                                                        "$$this.k",
                                                                    ]
                                                                },
                                                                "then": "$$this.v",
                                                                "else": "$$value",
                                                            }
                                                        },
                                                    }
                                                },
                                            ]
                                        },
                                    }
                                }
                            },
                            0,
                        ]
                    }
                }
            }
        ]
        lender_doc = self.collection.aggregate(pipeline)
        for doc in lender_doc:
            for transaction in doc["Transactions"]:
                try:
                    if doc["Transactions"][transaction]["Lender"] == str(username):
                        row = []
                        row.append(doc["Borrower"])
                        row.append(doc["Transactions"][transaction]["Lender"])
                        row.append(doc["Transactions"]
                                   [transaction]["Amount Given"])
                        row.append(doc["Transactions"]
                                   [transaction]["Currency Given"])
                        row.append(doc["Transactions"][transaction]["Given?"])
                        row.append(doc["Transactions"]
                                   [transaction]["Amount Repaid"])
                        row.append(doc["Transactions"]
                                   [transaction]["Currency Repaid"])
                        if doc["Transactions"][transaction]["Completed?"] == True:
                            row.append(True)
                        else:
                            row.append(False)
                        row.append(doc["Orignal Thread"])
                        row.append(doc["Transactions"]
                                   [transaction]["Date Given"])
                        row.append(doc["Transactions"]
                                   [transaction]["Date Paid Back"])
                        if doc["Transactions"][transaction]["Completed?"] == True:
                            count_lender_completed += 1
                            completed_amount = float(
                                doc["Transactions"][transaction]["Amount Repaid"])
                            completed_currency = doc["Transactions"][transaction]["Currency Repaid"]
                            amount_lender_completed += float(
                                c.convert(completed_amount, completed_currency, "USD"))
                        elif doc["Transactions"][transaction]["UNPAID?"] == True:
                            count_lender_unpaid += 1
                            unpaid_amount = float(
                                doc["Transactions"][transaction]["Amount Repaid"])
                            unpaid_currency = doc["Transactions"][transaction]["Currency Repaid"]
                            amount_lender_unpaid += float(
                                c.convert(unpaid_amount, unpaid_currency, "USD"))
                        else:
                            count_lender_ongoing += 1
                            ongoing_amount = float(
                                doc["Transactions"][transaction]["Amount Repaid"])
                            ongoing_currency = doc["Transactions"][transaction]["Currency Repaid"]
                            amount_lender_ongoing += float(
                                c.convert(ongoing_amount, ongoing_currency, "USD"))
                        l.append(row)
                except Exception as e:
                    print(e)
        if len(l) < 7:
            o += create_table_from_list(l)
        else:
            if count_borrower_completed == 0:
                o += f"u/{str(username)} has no loans completed as Borrower\n\n"
            else:
                o += f"u/{str(username)} has {count_borrower_completed} Loans Completed as Borrower for a total of ${count_borrower_completed_amount}\n\n"
            if count_lender_completed == 0:
                o += f"u/{str(username)} has no loans completed as Lender\n\n"
            else:
                o += f"u/{str(username)} has {count_lender_completed} Loans Completed as Lender for a total of ${amount_lender_completed}\n\n"
            if count_borrower_unpaid == 0:
                o += f"u/{str(username)} has not received any loans which are currently marked unpaid\n\n"
            else:
                o += f"u/{str(username)} has {count_borrower_unpaid} Loans Unpaid as Borrower for a total of ${amount_borrower_unpaid}\n\n"
            if count_lender_unpaid == 0:
                o += f"u/{str(username)} has not given any loans which are currently marked unpaid\n\n"
            else:
                o += f"u/{str(username)} has {count_lender_unpaid} Loans Unpaid as Lender for a total of ${amount_lender_unpaid}\n\n"
            if count_borrowed_ongoing == 0:
                o += f"u/{str(username)} has no loans ongoing as Borrower\n\n"
            else:
                o += f"u/{str(username)} has {count_borrowed_ongoing} Loans Ongoing as Borrower for a total of ${amount_borrower_ongoing}\n\n"
            if count_lender_ongoing == 0:
                o += f"u/{str(username)} has no loans ongoing as Lender\n\n"
            else:
                o += f"u/{str(username)} has {count_lender_ongoing} Loans Ongoing as Lender for a total of ${amount_lender_ongoing}\n\n"
        return o

    def unpaid(self, comment):
        try:
            regex = r"\$unpaid\s+(\d{5})"
            match = re.match(regex, comment.body)
            if match:
                paid_with_id = match.group(1)
                doc1 = self.post_collection.find_one({"ID": paid_with_id})
                if not doc1:
                    message = f"Invalid ID. Please check the ID and try again."
                    comment.reply(message)
                    return
                post_url = doc1["Orignal Thread"]
                post = self.reddit.submission(url=post_url)
                myquery = {"Orignal Thread": post_url}
                doc = self.collection.find_one(myquery)
                arr = doc["Transactions"]
                transaction = arr[paid_with_id]
                if comment.author != transaction["Lender"]:
                    comment.reply(
                        "You cannot mark someone else's transaction as unpaid"
                    )
                    return
                if transaction["Completed?"] == True:
                    comment.reply(
                        "This transaction has already been completed")
                    return
                if transaction["Lender"] == str(post.author):
                    comment.reply(
                        "You cannot mark your own transaction as unpaid")
                    return
                if transaction["UNPAID?"] == "**UNPAID**":
                    comment.reply(
                        "This transaction has already been marked as unpaid")
                    return
                arr[paid_with_id]["UNPAID?"] = "**UNPAID**"
                newvalues = {"$set": {"Transactions": arr}}
                self.collection.update_one(myquery, newvalues)
                o = f"Sorry to hear that about u/{str(post.author)}\n\n"
                o += self.get_user_details(str(post.author))
                comment.reply(o)
            else:
                message = f"Invalid Command Format. The correct format is ```$unpaid <5_digit transaction_id>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def handle_new_post(self, post):
        print(f"New post: {post.title}")
        if str(post.title).startswith("[REQ]"):
            self.handle_req_post(post)
        elif str(post.title).startswith("[PAID]"):
            self.handle_paid_post(post)
        elif str(post.title).startswith("[UNPAID]"):
            self.handle_unpaid_post(post)
        elif str(post.title).startswith("[OFFER]"):
            self.handle_offer_post(post)
        else:
            self.handle_wrong_post(post)

    def handle_wrong_post(self, post):
        try:
            o = "Please use the correct Post format\n\n"
            o += "You can use one of the following post formats :\n\n"
            o += "```[REQ] (Amount) (Currency) - (#City, State, Country), (Repayment Date), (Payment Method)```\n\n"
            o += "Example: [REQ] (100.00) (USD) - (New York City, New York, United States), (2023-05-01), (PayPal)\n\n\n\n"
            o += "```[PAID] (username) - (amount) (other information)```\n\n"
            o += "Example: [PAID] (u\\username) - (100.0) (On Time)\n\n\n\n"
            o += "```[UNPAID] (username) - (amount) (information)```\n\n"
            o += "Example: [UNPAID] (u/username) - (100.0) (Overdue)\n\n\n\n"
            o += "```[OFFER] - (your offer)```\n\n"
            o += "Example: [OFFER] - (I have some money, I'd like to offer someone)\n\n\n\n"
            post.reply(o)
            post.mod.remove()
        except:
            print("Error")

    def handle_offer_post(self, post):
        try:
            regex = self.OFFER_POST_REGEX
            match = re.match(regex, str(post.title))
            if match:
                o = self.get_user_details(str(post.author))
                post.reply(o)
            else:
                o = "Please follow the format\n\n"
                o += "[OFFER] - (your offer)\n\n"
                o += "Example: [OFFER] - (I have some money, I'd like to offer someone)\n\n"
                post.reply(o)
                post.mod.remove()
        except Exception as e:
            print(e)

    def handle_unpaid_post(self, post):
        try:
            regex = self.UNPAID_POST_REGEX
            match = re.match(regex, str(post.title))
            if match:
                o = self.get_user_details(str(post.author))
                post.reply(o)
            else:
                o = "Please follow the format\n\n"
                o += "[UNPAID] (username) - (amount) (information)\n\n"
                o += "Example: [UNPAID] (u/username) - (100.0) (Overdue)\n\n"
                post.reply(o)
                post.mod.remove()
        except Exception as e:
            print(e)

    def handle_paid_post(self, post):
        try:
            regex = self.PAID_POST_REGEX
            match = re.match(regex, str(post.title))
            if match:
                o = self.get_user_details(str(post.author))
                post.reply(o)
            else:
                o = "Please follow the format\n\n"
                o += "[PAID] (username) - (amount) (other information)\n\n"
                o += "Example: [PAID] (u\\username) - (100.0) (On Time)\n\n"
                post.reply(o)
                post.mod.remove()
        except Exception as e:
            print(e)

    def handle_req_post(self, post):
        try:
            regex = self.REQ_POST_REGEX
            match = re.match(regex, str(post.title))
            if match:
                amt = float(match.group(1))
                currency = match.group(2).upper()
                if currency not in currencies_supported:
                    message = f"Currency not supported. Please check the currency and try again."
                    message += "\n\nSupported Currencies: ```"
                    for currency in currencies_supported:
                        message += f"{currency}, "
                    message += "```"
                    post.reply(message)
                    post.mod.remove()
                    return
                amt_in_USD = round(c.convert(amt, currency, "USD"), 2)
                o = str(self.get_user_details(post.author))
                o += f"\nCommand to loan should be ```$loan {str(amt_in_USD)} USD```\n"
                post.reply(o)
            else:
                print("INSIDE ELSE")
                o = "Please follow the format\n\n"
                o += "[REQ] (Amount) (Currency) - (#City, State, Country), (Repayment Date and Repayment amount), (Payment Method)\n\n"
                o += "Example: [REQ] (100.00) (USD) - (New York City, New York, United States), (2023-05-01), (PayPal)\n\n"
                post.reply(o)
                post.mod.remove()
        except Exception as e:
            print(e)

    def loan(self, comment):
        try:
            regex = self.LOAN_REGEX
            match = re.match(regex, str(comment.body).strip())
            if match:
                post = comment.submission
                if not (str(post.title).strip().startswith("[REQ]")):
                    comment.reply(
                        "Please only use this command in a Request Post.")
                    return
                post_url = post.url
                myquery = {"Orignal Thread": post_url}
                doc = self.collection.find_one(myquery)
                if not doc:
                    regex2 = self.REQ_POST_REGEX
                    match2 = re.match(regex2, str(post.title))
                    post_amount = float(match2.group(1))
                    post_currency = match2.group(2).upper()
                    post_amount = round(
                        c.convert(post_amount, post_currency, "USD"), 2)
                    doc = {
                        "Borrower": str(post.author),
                        "Amount Requested": float(match2.group(1)),
                        "Currency": post_currency,
                        "Amount Given": 0,
                        "Amount Repaid": 0,
                        "Orignal Thread": post.url,
                        "Transactions": {},
                    }
                    self.collection.insert_one(doc)
                arr = doc["Transactions"]
                loan_amount_given = float(match.group(1))
                loan_currency_given = match.group(3).upper()
                if loan_currency_given not in currencies_supported:
                    message = f"Currency not supported. Please check the currency and try again."
                    message += "\n\nSupported Currencies: ```"
                    for currency in currencies_supported:
                        message += f"{currency}, "
                    message += "```"
                    comment.reply(message)
                    return
                loan_amount_in_USD = round(
                    c.convert(loan_amount_given, loan_currency_given, "USD"), 2
                )
                amount_give_till_now = float(doc["Amount Given"])
                loan_amount_max_asked = float(
                    re.match(
                        self.REQ_POST_REGEX,
                        comment.submission.title,
                    ).group(1)
                )
                loan_amount_max_asked = round(c.convert(
                    loan_amount_max_asked, match2.group(2), "USD"
                ), 2)
                lender_name = comment.author.name
                borrower_name = comment.submission.author
                paid_with_id = str(random.randint(10000, 99999))
                query = {"ID": paid_with_id}
                while self.post_collection.find_one(query) != None:
                    paid_with_id = str(random.randint(10000, 99999))
                    query = {"ID": paid_with_id}
                if borrower_name == lender_name:
                    message = f"[{borrower_name}](/u/{borrower_name})-Borrower dont have access to write this command."
                    comment.reply(message)
                elif (
                    loan_amount_max_asked - amount_give_till_now >= loan_amount_in_USD
                    and loan_amount_in_USD > 0
                ):
                    new_doc = {
                        "Lender": str(comment.author),
                        "ID": paid_with_id,
                        "Amount Given": loan_amount_given,
                        "Currency Given": loan_currency_given,
                        "Given?": False,
                        "Amount Repaid": 0,
                        "Currency Repaid": None,
                        "UNPAID?": "",
                        "Date Given": datetime.datetime.now(),
                        "Date Paid Back": None,
                        "Completed?": False,
                    }
                    arr[paid_with_id] = new_doc
                    newvalues = {"$set": {"Transactions": arr}}
                    self.collection.update_one(myquery, newvalues)

                    highlighted_text_1 = "$confirm {} {} {}".format(
                        paid_with_id, loan_amount_given, loan_currency_given
                    )
                    highlighted_text_2 = "$repaid_with_id {} {} {}".format(
                        paid_with_id, loan_amount_given, loan_currency_given
                    )

                    new_doc = {
                        "Borrower": str(comment.submission.author),
                        "Lender": str(comment.author),
                        "Orignal Thread": post_url,
                        "ID": paid_with_id,
                    }
                    self.post_collection.insert_one(new_doc)
                    message = (
                        f"Noted! I will remember that [{lender_name}](/u/{lender_name}) lent {loan_amount_given} {loan_currency_given} to [{borrower_name}](/u/{borrower_name})\n\n"
                        f"```The unique id for this transaction is - {paid_with_id}```\n\n"
                        f"The format of the confirm command will be:\n\n"
                        f"```{highlighted_text_1}```"
                        f"\n\nIf you wish to mark this loan repaid later, you can use:\n\n"
                        f"```{highlighted_text_2}```"
                        f"\n\n  "
                        f"\n\nThis does NOT verify that [{lender_name}](/u/{lender_name}) actually lent anything to [{borrower_name}](/u/{borrower_name});\n\n "
                        f"[{borrower_name}](/u/{borrower_name}) should confirm here or nearby that the money was sent"
                        f"\n\n**If the loan transaction did not work out and needs to be refunded then the lender should"
                        f" reply to this comment with 'Refunded' and moderators will be automatically notified**"
                    )
                    comment.reply(message)
                else:
                    if loan_amount_max_asked - amount_give_till_now == 0:
                        message = f"[{comment.author}](/u/{comment.author}) \n This loan request has been fulfilled."
                    else:
                        message = f"[{comment.author}](/u/{comment.author}) \n Maximum Amount you can Lend is {loan_amount_max_asked-amount_give_till_now} $"
                    comment.reply(message)
            else:
                message = f"Invalid Command Format. The correct format is ```$loan <amount>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def confirm(self, comment):
        try:
            regex = self.CONFIRM_REGEX
            match = re.match(regex, comment.body)
            if match:
                paid_with_id = match.group(1)
                doc1 = self.post_collection.find_one({"ID": paid_with_id})
                if not doc1:
                    message = f"Invalid ID. Please check the ID and try again."
                    comment.reply(message)
                    return
                post_url = doc1["Orignal Thread"]
                post = self.reddit.submission(url=post_url)
                myquery = {"Orignal Thread": post_url}
                doc = self.collection.find_one(myquery)
                existing_amt_given = doc["Amount Given"]
                amount_requested = doc["Amount Requested"]
                transactions = doc["Transactions"]
                comment_amount_received = float(match.group(2))
                comment_currency_received = match.group(3).upper()
                borrower_name = post.author
                comment_author = comment.author
                lender_name = transactions[paid_with_id]["Lender"]
                lender_actual_amount_given = float(
                    transactions[paid_with_id]["Amount Given"]
                )
                lender_currency_given = transactions[paid_with_id]["Currency Given"]

                if paid_with_id in transactions:
                    if borrower_name != comment_author:
                        message = f"[{lender_name}](/u/{lender_name}), is not authorized to confirm this loan. Only [{borrower_name}](/u/{borrower_name}) can do this."
                        comment.reply(message)
                        return

                    if comment_currency_received != lender_currency_given:
                        message = f"[{borrower_name}](/u/{borrower_name}), the loan cannot be confirmed.\n\n The Currency {comment_currency_received} you are confirming, doesnt match the currency what [{lender_name}](/u/{lender_name}) has paid"
                        comment.reply(message)
                        return

                    if comment_amount_received != lender_actual_amount_given:
                        message = f"[{borrower_name}](/u/{borrower_name}), the loan cannot be confirmed.\n\n The Amount {comment_amount_received} $ you are confirming, doesnt match the amount what [{lender_name}](/u/{lender_name} has paid"
                        comment.reply(message)
                        return
                    transactions[paid_with_id]["Given?"] = True
                    existing_amt_given += float(comment_amount_received)

                    message = (
                        f"[{borrower_name}](/u/{borrower_name}) has just confirmed that [{lender_name}](/u/{lender_name}) gave him/her {comment_amount_received} {comment_currency_received}. (Reference amount: {amount_requested}). We matched this confirmation with this [loan]({post_url}) (id={paid_with_id}).\n\n"
                        f"___________________________________________________"
                        f"\n\nThe purpose of responding to $confirm is to ensure the comment doesn't get edited.\n"
                    )
                    comment.reply(message)
                    myquery = {"Orignal Thread": post_url}
                    newvalues = {
                        "$set": {
                            "Transactions": transactions,
                            "Amount Given": existing_amt_given,
                        }
                    }
                    self.collection.update_one(myquery, newvalues)
                else:
                    message = (
                        f"Cannot Confirm!\n\n"
                        f"**[{lender_name}](/u/{lender_name}** has given them amount of **{comment_amount_received}** {comment_currency_received} to **[{borrower_name}](/u/{borrower_name})**"
                    )
                    comment.reply(message)
            else:
                message = f"Invalid Command Format. The correct format is ```$confirm <5 digit id> <amount> <optional_currency>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def repaid_with_id(self, comment):
        try:
            regex = self.REPAID_REGEX
            match = re.match(regex, comment.body)
            if match:
                id = match.group(1)
                doc1 = self.post_collection.find_one({"ID": id})
                if not doc1:
                    message = f"Invalid ID. Please check the ID and try again."
                    comment.reply(message)
                    return
                post_url = doc1["Orignal Thread"]
                post = self.reddit.submission(url=post_url)
                myquery = {"Orignal Thread": post_url}
                doc = self.collection.find_one(myquery)
                transactions = doc["Transactions"]
                comment_amount_repaid = float(match.group(2))
                comment_currency_repaid = match.group(3).upper()
                if comment_currency_repaid not in currencies_supported:
                    message = f"Currency not supported. Please check the currency and try again."
                    message += "\n\nSupported Currencies: ```"
                    for currency in currencies_supported:
                        message += f"{currency}, "
                    message += "```"
                    comment.reply(message)
                    return
                borrower_name = post.author
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
                    comment_amount_repaid_in_USD = c.convert(
                        comment_amount_repaid, comment_currency_repaid, "USD")
                    actual_amount_given_in_USD = c.convert(float(
                        transactions[id]["Amount Given"]), transactions[id]["Currency Given"], "USD")
                    if abs(comment_amount_repaid_in_USD - actual_amount_given_in_USD) > 0.1:
                        try:
                            message = f"Hi {str(comment.author)}, the amount you have entered to mark this loan as repaid is not the same as the amount given in the transaction. Please enter the correct amount."
                            correct_amount = c.convert(
                                float(transactions[id]["Amount Given"]), transactions[id]["Currency Given"], comment_currency_repaid)
                            message += f"\n\nThe correct amount is in range of {round(correct_amount - 0.01,3)} to {round(correct_amount + 0.01,3)} {comment_currency_repaid}"
                            # Give disclaimer that currency converter might be wrong
                            message += "\n\n**Disclaimer:** The currency converter might be wrong. Please check the correct amount manually but enter the amount shown above."
                            comment.reply(message)
                            return
                        except Exception as e:
                            print(e)
                            # currency conversion not supported. Ask user to exact amount given in exact currency.
                            message = f"The currency you have entered is not supported. Please enter the exact amount given in given currency."
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
                    transactions[id]["Amount Repaid"] += float(
                        comment_amount_repaid)
                    transactions[id]["Currency Repaid"] = comment_currency_repaid
                    transactions[id]["Date Paid Back"] = datetime.datetime.now()
                    newvalues = {
                        "$set": {
                            "Transactions": transactions,
                        }
                    }
                    self.collection.update_one(myquery, newvalues)
                    message = (
                        f"Hi {str(comment.author)}, your loan of {comment_amount_repaid} from [{lender_name}](/u/{lender_name}) has noted successfully. To confirm [{lender_name}](/u/{lender_name}) must reply with the following:"
                        f"""
                    \n\n```$repaid_confirm {id} {comment_amount_repaid} {comment_currency_repaid}```"""
                        f"\n\n**Transaction ID:** {id} **Date Repaid:** {datetime.datetime.now()}"
                    )
                    self.collection.update_one(myquery, newvalues)
                else:
                    message = f"Transaction ID not found. Please check command again."
                comment.reply(message)
            else:
                message = f"Invalid Command Format. The correct format is ```$repaid_with_id <5 digit id> <amount> <USD>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def repaid_confirm(self, comment):
        try:
            regex = self.REPAID_CONFIRM_REGEX
            match = re.match(regex, comment.body)
            if match:
                id = match.group(1)
                doc1 = self.post_collection.find_one({"ID": id})
                if not doc1:
                    message = f"Invalid ID. Please check the ID and try again."
                    comment.reply(message)
                    return
                post_url = doc1["Orignal Thread"]
                myquery = {"Orignal Thread": post_url}
                doc = self.collection.find_one(myquery)
                current_repaid_amount = float(doc["Amount Repaid"])
                transactions = doc["Transactions"]
                comment_author = comment.author
                comment_amount_repaid = float(match.group(2))
                comment_currency_repaid = match.group(3).upper()
                borrower_name = comment.submission.author
                id = match.group(1)
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
                    if comment_amount_repaid != transactions[id]["Amount Repaid"]:
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

                    # Check if currency is not same
                    if comment_currency_repaid != transactions[id]["Currency Repaid"]:
                        message = f"Hi {str(comment.author)}, the currency you have entered to confirm this loan as repaid is not the same as the currency given in the transaction. Please enter the correct currency."
                        comment.reply(message)
                        return

                    # update completed to true and add amount repaid to current repaid amount
                    transactions[id]["Completed?"] = True
                    current_repaid_amount += float(comment_amount_repaid)
                    newvalues = {
                        "$set": {
                            "Transactions": transactions,
                            "Amount Repaid": current_repaid_amount,
                        }
                    }

                    self.collection.update_one(myquery, newvalues)
                    message = f"Hi {str(comment.author)}, the loan of {comment_amount_repaid} to [{borrower_name}](/u/{borrower_name}) has been completed successfully."
                    f"\n\n**Transaction ID:** {id} **Date Repaid:** {datetime.datetime.now()}"
                    self.collection.update_one(myquery, newvalues)
                else:
                    message = f"Transaction ID not found. Please check command again."
                comment.reply(message)
            else:
                message = f"Invalid Command Format. The correct format is ```$repaid_confirm <5 digit id> <amount>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def check(self, comment):
        try:
            regex1 = r"\$check\s+u/(\w+)"
            match1 = re.match(regex1, comment.body)
            regex2 = r"\$check\s+\[([^]]+)\]"
            match2 = re.match(regex2, comment.body)
            regex3 = r"\$check\s+(\w+)"
            match3 = re.match(regex3, comment.body)
            user_id = False
            if match1:
                user_id = match1.group(1)
            elif match2:
                user_id = match2.group(1)
            elif match3:
                user_id = match3.group(3)

            if user_id != False:
                print(comment.body)
                o = self.get_user_details(user_id)
                comment.reply(o)
            else:
                message = f"Invalid Command Format. The correct format is ```$check <user_id>```"
                comment.reply(message)
        except Exception as e:
            print(e)

    def help_command(self, comment):
        message = "Here are the available commands: "
        message += " \n\n"
        message += " ```$check <user_id>``` - Check the status of a user. "
        message += " \n\n"
        message += " ```$help``` - Get help with the commands. "
        message += " \n\n"
        message += " ```$loan <amount>``` - Offer a loan to the author of the post. "
        message += " \n\n"
        message += " ```$confirm <transaction_id> <amoount>``` - Confirm a loan with the given transaction id. "
        message += " \n\n"
        message += " ```$repaid_with_id <transaction_id> <amount>``` - Inform that the loan has been repaid with the given transaction id. "
        message += " \n\n"
        message += " ```$repaid_confirm <transaction_id> <amount>``` - Confirm that the loan has been repaid with the given transaction id. "
        message += " \n\n"
        message += " ```$unpaid <transaction_id>``` - Marks the transaction as unpaid. "
        message += " \n\n"
        comment.reply(message)

    def handle_new_comment(self, comment):
        try:
            print(f"New Comment:", comment.body)
            if comment.body.strip().startswith("$"):
                command = comment.body.split()[0].lower()[1:]
                if command in self.commands:
                    self.commands[command](comment)
                else:
                    message = "Invalid Command!"
                    comment.reply(message)
        except Exception as e:
            print(e)

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
        target_subreddit=credentials.subreddit_name,
    )
    bot.start()
