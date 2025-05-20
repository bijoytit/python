# while True:
#     print('Input name')
#     name= input()
#     if name != 'bijoy':
#         continue
#     print('input password')
#     password=input()
#     if password == '1234':
#         break
# print ('Welcome')

# while True:
#     print('input name')
#     name = input()
#     if name != 'bijoy':
#         continue
#     print('input pass')
#     passwd = input()
#     if passwd == '1234':
#         print('access grant')
#         break

# while True:
#     name = input()
#     age = int(input())
#     fee = 10
#     age_max = 18
#     application_fee = age > age_max
#     cal_fee = fee + 100 if application_fee else print('No fee')
#     print (cal_fee)
while True:
    ###
# Fee Calculator: Calculates 1% fee for transactions above threshold
# Supports BDT (>10000) and USD (>100)
    print("Enter currency (BDT or USD):")
    currency = input().upper()
    if currency not in ["BDT", "USD"]:
        print("Error: Only BDT or USD supported")
    else:
        print(f"Enter transaction amount ({currency}):")
        try:
            amount = float(input())
            if amount < 0:
                print("Error: Amount cannot be negative")
            else:
                threshold = 10000 if currency == "BDT" else 100
                fee_rate = 0.01
                applies_fee = amount > threshold
                fee = amount * fee_rate if applies_fee else 0
                total = amount + fee
                print(f"Amount: {currency} {amount:.2f}")
                print(f"Fee: {currency} {fee:.2f}")
                print(f"Total: {currency} {total:.2f}")
        except ValueError:
            print("Error: Please enter a valid number")
