import json
import time

# codespecialist.com https://www.youtube.com/watch?v=FKgJEfrhU1E
import os
import pathlib

import requests
from . import my_db, pb
from pymongo import MongoClient

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, session, abort, redirect, request, render_template, flash
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from .config import config


db = my_db.db
app = Flask(__name__)
app.secret_key = config.get("APP_SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = config.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

GOOGLE_CLIENT_ID = (
    config.get("GOOGLE_CLIENT_ID"))

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, ".client_secrets.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="https://sd3aiot.online/callback",
)

alive=0
data={}

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token, request=token_request, audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    print(session["google_id"])
    session["name"] = id_info.get("name")
    print(session["name"])
    return redirect("/protected_area")


@app.route("/logout")
def logout():
    my_db.user_logout(session['google_id'])
    session.clear()
    return redirect("/")


@app.route("/protected_area")
@login_is_required
def protected_area():
    my_db.add_user_and_login(session['name'], session['google_id'])
    return render_template("protected_area.html", user_id = session['google_id'],google_admin_id = config.get("GOOGLE_ADMIN_ID"), online_users = my_db.get_all_logged_in_users())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/keep_alive")
def keep_alive():
    global alive, data
    alive += 1
    keep_alive_count = str(alive)
    data["keep_alive"] = keep_alive_count
    parsed_json = json.dumps(data)
    return str(parsed_json)


@app.route('/grant-<user_id>-<read>-<write>', methods=["POST"])
def grant_access(user_id, read, write):
    if session.get('google_id'):
        if session['google_id'] == config.get("GOOGLE_ADMIN_ID"):
            print(f"Admin granting {user_id}-{read}-{write}")
            my_db.add_user_permission(user_id, read, write)
            if (read=="true" or read==True) and (write=="true" or write==True):
                token = pb.grant_read_and_write_access(user_id)
                my_db.add_token(user_id, token)
                return token
            elif read=="true" and write=="false":
                token = pb.grant_read_access(user_id)
                my_db.add_token(user_id, token)
                access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id}
                return json.dumps(access_response)
            elif read=="false" and write=="true":
                token = pb.grant_write_access(user_id)
                my_db.add_token(user_id, token)
                access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id}
                return json.dumps(access_response)
            else:
                #Remove any existing token from the database
                my_db.delete_revoked_token(user_id)
                access_response={'token':123, 'cipher_key':pb.cipher_key, 'uuid':user_id}
                return json.dumps(access_response)
        else:
            print(f"Non admin attempting to grant privileges {user_id}-{read}-{write}")
            my_db.add_user_permission(user_id, read, write)
            token = my_db.get_token(user_id)
            if token is not None:
                timestamp, ttl, user_id, read, write = pb.parse_token(token)
                current_time = time.time
                if(timestamp + (ttl*60)) - current_time > 0:
                    print("Token is still valid")
                    access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id} 
                    return json.dumps(access_response)
                else:
                    print("Token refresh needed")
                    if read and write:
                        token = pb.grant_read_write_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id} 
                        return json.dumps(access_response)
                    elif read:
                        token = pb.grant_read_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id} 
                        return json.dumps(access_response)
                    elif read:
                        token = pb.gran_write_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response={'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id} 
                        return json.dumps(access_response)
                    else:
                        access_response={'token':123, 'cipher_key':pb.cipher_key, 'uuid':user_id}
                        return json.dumps(access_response)
  

@app.route('/get_user_token', methods=['POST'])
def get_user_token():
    user_id = session['google_id']
    token = my_db.get_token(user_id)
    if token is not None:
        token = get_or_refresh_token(token)
        token_response = {'token':token, 'cipher_key':pb.cipher_key, 'uuid':user_id}
    else:
        token_response = {'token':123, 'cipher_key':pb.cipher_key, 'uuid':user_id}
    return token_response


def get_or_refresh_token(token):
    timestamp, ttl, uuid, read, write = pb.parse_token(token)
    current_time = time.time()
    if(timestamp+(ttl*60)) - current_time > 0:
        return token
    else:
        # The token has expired
        return grant_access(uuid, read, write)


if __name__ == "__main__":
    app.run()
