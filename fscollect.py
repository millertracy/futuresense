from futuresense import FutureSense
import ast
from concurrent import futures

with open('users.csv', 'r') as f:
    users = ast.literal_eval(f.read())
users = users.keys()
users.remove('sandbox8')

def get_data(user)
    fs = FutureSense(user=user, sandbox=True)
    fs.get_all(all_startday='1/1/2015', all_reps=35)

executor = futures.ThreadPoolExecutor(10)
future = [executor.submit(get_data, user)
            for user in users]
futures.wait(future)
