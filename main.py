from datetime import datetime, timedelta
from typing import Optional

import json
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from passlib.context import CryptContext

from pydantic import BaseModel

with open("menu.json", "r") as read_file:
    data = json.load(read_file)
app = FastAPI()

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


fake_users_db = {
    "asdf": {
        "username": "asdf",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$OS5wetnUfg3Lzek.rGNG6.CHjmK5uILdLnrjZZt53WaYvm7zW2I8u",
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()



def verify_password(plain_password, hashed_password):

    return pwd_context.verify(plain_password, hashed_password)




def get_password_hash(password):

    return pwd_context.hash(password)



def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)



def authenticate_user(fake_db, username: str, password: str):

    user = get_user(fake_db, username)

    if not user:

        return False

    if not verify_password(password, user.hashed_password):

        return False

    return user



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]

@app.get("/") 
async def root(current_user: User = Depends(get_current_active_user)):
	return data['menu']

@app.get('/menu/{item_id}')
async def read_menu(item_id:int, current_user: User = Depends(get_current_active_user)):
	for menu_item in data['menu']:
		if menu_item['id']==item_id:
			return menu_item
	raise HTTPException(
		status_code=404,detail=f'Item not found'
	)

@app.delete('/menu/remove/{item_id}')
async def delete_menu(item_id:int, current_user: User = Depends(get_current_active_user)):
	new_list=[]
	for menu_item in data['menu']:
		if menu_item['id']!=item_id:
			new_list.append({"id":menu_item['id'],"name":menu_item['name']})
	data_dummy={"menu":new_list}
	with open('menu.json', 'w') as outfile:
		json.dump(data_dummy, outfile)
	return data_dummy

@app.put('/menu/update/{item_id}/{item_name}')
async def update_menu(item_id:int,item_name:str, current_user: User = Depends(get_current_active_user)):
	new_list=[]
	for menu_item in data['menu']:
		if menu_item['id']==item_id:
			menu_item['name']=item_name
		new_list.append(menu_item)
	data_dummy={"menu":new_list}
	with open('menu.json', 'w') as outfile:
		json.dump(data_dummy, outfile)
	return data_dummy
    
@app.post('/menu/add/{item_id}/{item_name}')
async def add_menu(item_id:int,item_name:str, current_user: User = Depends(get_current_active_user)):
	data['menu'].append({'id':item_id,'name':item_name})
	with open('menu.json', 'w') as outfile:
		json.dump(data, outfile)
	return data