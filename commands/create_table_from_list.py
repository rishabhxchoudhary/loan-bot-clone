# code a function which gives reddit markdown table if a list of strings is given as input.

def create_table_from_list(l):
    final_string=""
    for i in range(len(l)):
        row="|"
        for j in range(len(l[i])):
            row+=l[i][j]+"|"
        row+='\n'
        if i==0:
            row+=":--|"*(j+1)
        row+='\n'
        final_string+=row
    return final_string

l = [
    ["Lender","Borrower","Amount Given","Amount Repaid","Orignal Thread","Date Given","Date Paid Back"],
    ["frumboldt21","mother_customer7570","500.00 USD","120.00 USD","https://www.reddit.com/comments/114z3yv/redditloans/j8z0nj7","Feb 17, 2023",""]
    ]

print(create_table_from_list(l))