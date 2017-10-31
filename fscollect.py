from futuresense import FutureSense
import ast
from concurrent import futures
import pymongo

with open('users.csv', 'r') as f:
    users = ast.literal_eval(f.read())
users = users.keys()
users.remove('sandbox8')

def get_data(user):
    fs = FutureSense(user=user, sandbox=False)
    fs.get_all(all_reps=4)


# executor = futures.ThreadPoolExecutor(10)
# future = [executor.submit(get_data, user)
#             for user in users]
# futures.wait(future)

get_data('djo')
