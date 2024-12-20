let aliveSecond = 0;
let heartBeatRate = 100000;
let pubnub;
let appChannel = "johns_pi_channel";
let ttl = 5;


//sendEvent('get_user_token');

function refresh_token()
{
    sendEvent('get_user_token');
    let refresh_time = (ttl-1)*60*1000;
    console.log(refresh_time);
    setTimeout('refresh_token()', refresh_time);
}

function time()
{
    let d = new Date();
    let currentSecond = d.getTime();
    if(currentSecond - aliveSecond > heartBeatRate + 1000)
    {
        document.getElementById("connection_id").innerHTML="DEAD";
    }
    else
    {
        document.getElementById("connection_id").innerHTML="ALIVE";
    }
    setTimeout('time()', 1000);
}

function keepAlive()
{
    fetch('/keep_alive')
    .then(response=>{
        if(response.ok){
            let date = new Date();
            aliveSecond = date.getTime();
            return response.json();
        }
        throw new Error("Server offline");
    })
    .catch(error=>console.log(error));
    setTimeout('keepAlive()', heartBeatRate);
}

function handleClick(cb)
{
    if(cb.checked)
    {
        value="on";
    }
    else
    {
        value = "off";
    }
    const cryptoModule = PubNub.CryptoModule.legacyCryptoModule({
        cipherKey: "secret-123"
    });
    console.log(cryptoModule.encrypt('{"buzzer":value}'))
    publishMessage({"buzzer" : value})
}

const setupPubNub = () => {
    pubnub = new PubNub({
        publishKey: 'pub-c-6ce775ac-3b15-47e0-937b-e5bd7cf6c79d',
        subscribeKey: 'sub-c-6eb23377-44fd-4c6e-b456-974c422b6cc7',
        cryptoModule: PubNub.CryptoModule.aesCbcCryptoModule({cipherKey: 'secret-123'}),
        userId: "test-123"
    });
    //create a channel
    const channel = pubnub.channel(appChannel);
    //create a subscription
    const subscription = channel.subscription();

    pubnub.addListener({
        status: (s) =>{
            console.log('Status', s.category);
        },
    });

    subscription.onMessage = (messageEvent) => {
        handleMessage(messageEvent.message);
    };

    subscription.subscribe();
};

const publishMessage = async(message) => {
    const publishPayload = {
        channel : appChannel,
        message : message,
    };
    await pubnub.publish(publishPayload);
};

function handleMessage(message)
{ 
    console.log(message);
    if(message == '"Motion":"Yes"')
    {
        document.getElementById("motion_id").innerHTML = "Yes";
    }
    if(message == '"Motion":"No"')
    {
        document.getElementById("motion_id").innerHTML = "No";
    }
}

function logout()
{
    location.replace("/logout");
}

function grantAccess(ab)
{
    let userId = ab.id.split("-")[2];
    let readState = document.getElementById("read-user-"+userId).checked;
    let writeState = document.getElementById("write-user-"+userId).checked;
    console.log("grant-"+userId+"-"+readState+"-"+writeState);
    sendEvent("grant-"+userId+"-"+readState+"-"+writeState);
}


function sendEvent(value)
{
    fetch(value,
    {
        method:"POST",
    })
    .then(response => response.json())
    .then(responseJson => {
        console.log(responseJson);
        if(responseJson.hasOwnProperty('token'))
        {
            pbToken = responseJson.token;
            pubnub.setToken(pbToken);
            console.log("Cipher Key: " + responseJson.cipher_key);
            //pubnub.setCipherKey(responseJson.cipher_key);
            pubnub.setUUID(responseJson.uuid);
            subscribe();
        }
    });
}


function subscribe()
{
    console.log("Trying to subscribe with token");
	//pubnub.subscribe({channels:[appChannel]});
    const channel = pubnub.channel(appChannel);
    //create a subscription
    const subscription = channel.subscription();
    subscription.subscribe();
}

