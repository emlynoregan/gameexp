import os
import shutil

# copy the file local.env over .env
print ("Copying local.env to .env")
shutil.copyfile("local.env", ".env")

# now start the server
print ("Starting server")
os.system("react-scripts start")



