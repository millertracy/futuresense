from futuresense import FutureSense
import ast

with open('users.csv', 'r') as f:
    users = ast.literal_eval(f.read())
users = users.keys()
users.remove('sandbox8')

for user in users:
    fs = FutureSense(user=user, sandbox=True)
    fs.get_all(all_startday='1/1/2015', all_reps=35)
