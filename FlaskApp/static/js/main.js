let aliveSecond = 0;
let heartBeatRate = 5000;
let pubnub;
let appChannel = "johns_pi_channel";

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
    publishMessage({"buzzer" : value})
}

const setupPubNub = () => {
    pubnub = new PubNub({
        publishKey: 'your_publish_key',
        subscribeKey: 'your_subscribe_key',
        userId: "your_user_id",
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


