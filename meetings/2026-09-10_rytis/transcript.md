### Prof Rytis. Forest discussion

**Prof. Rytis:** Which we should be able to connect appropriate sensors and configure the firmware for some specific application.

**Ali:** But the problem is all of these mentioned in the work plan. So if you want to implement all these in 15 months, you know, I think that we might face problems.

**Prof. Rytis:** Why?

**Ali:** Because for each of them we have to gather the dataset, we have to train the dataset, we have to deploy it, deploy the trained model on the edge AI, we should go to the field to check if the model is working well. Because the distribution can be shifted so...

**Prof. Rytis:** Yeah, but some things can be simulated. I'm not sure if everything needs to be field tested.

**Ali:** Yes.

**Prof. Rytis:** Gas sensors, stuff like that... you can also make dummy data... Generate data for training and test. Even if you would have everything today, it's questionable that one year is enough to detect disease.

**Ali:** Mhm.

**Prof. Rytis:** It can take longer.

**Ali:** So how we are going to detect the disease? And which kind of disease we are going to detect?

**Prof. Rytis:** Well, one way is computer vision, which I don't think we should be doing in this project. Another way is change in the parameters of the tree. Change for example in tree sap flow... Which is basically resistance measure between two sensors... Change of the CO2 around the tree in the environment if it's rotting, something, stuff like that.

**Ali:** So you think that we can... we can implement all of these...

**Prof. Rytis:** I would put most suspicious ones like disease as good to have... So maybe Julius can negotiate that this will be for the future... maybe only lab tested... and select the most feasible ones.

**Ali:** Okay.

**Prof. Rytis:** Bear detection is probably very doable... Bear detection... Sound analysis is very doable... stuff like that. What is on the priority and what is good to have.

**Ali:** For example, I have not checked in the... in the internet for the data, but illegal logging also can be doable.

**Prof. Rytis:** Yeah, it's more sound based. Sound intensity, also some... breaking something, saw noises, engine noises, stuff like that.

**Ali:** Yes. So we should narrow down all these six, seven options to at least two, three options.

**Prof. Rytis:** Yes, and put the rest as potentially will be implemented in lab conditions but not field tested due to limited period of time for validation. Because these require long term monitoring which is not doable. Because you cannot detect disease over one month. You monitor it over the year. And the whole project is 15 months. So field deployment maybe could be on month 10. So it's still not possible. So we still need to do something, because it's disease in the project... but it could be like... a code that was trained on artificial values, it can classify etcetera. But it will not be field tested. And that is doable. You can ask ChatGPT what would be normal values... measure some normal values, then ask what would be the disease values and generate some dummy dataset. And train it like that and... test it in the lab conditions. But we will not field test.

**Ali:** Sure. So some of them yeah, can be tested on the lab not on the field...

**Prof. Rytis:** Yeah, because other than that it's just a change in time series parameters.

**Ali:** Yes.

**Prof. Rytis:** And also... you can ask your Arabic, Iranian... I don't know.

**Ali:** Yeah, it's Iranian. Persian.

**Prof. Rytis:** ...ChatGPT. What parameters define the disease and a typical IoT sensor installed in the forest... I think it will be humidities, change in CO2, because it's everything related to leaves. Healthiness of leaves, because if there are lots of dry leaves these parameters change. Probably temperature also changes in the shadows.

**Ali:** Well you know the trees in the... in the forest, they are more resistant to these kind of diseases compared to the other ones... which are in the garden...

**Prof. Rytis:** Yeah... take spruce for example... bark beetle effects. It dries up. The bark starts to peel off, the tree starts to dry up and you can well imagine something would be visible in the sap flow. If you want to speak about disease, I can arrange a meeting with VDU foresters... I think it would be a good...

**Ali:** Yeah definitely, sure. First...

**Prof. Rytis:** Drop me a message on telegram... on IT part, so I don't forget and give you the contact.

**Ali:** Sure, sure. I will probably come to VDU directly to them and speak. I don't mean we are also arranging a dataset for water...

**Prof. Rytis:** Yes, yes.

**Ali:** ...to discuss this as well, how to test validate...

**Prof. Rytis:** Sure, this this post for them also would be interesting. Just don't mention that it's a company project, they don't need to know... say that you're a PhD student working on the forest topic... forest project topic.

**Ali:** Forest project topic, sure. And umm... Based on what I understood from the scope of the project, we have some sensor nodes here.

**Prof. Rytis:** Yes.

**Ali:** We have microcontrollers, Edge AI, we have the LoRa, we have the Gateway.

**Prof. Rytis:** And concentrator... hopefully in that box...

**Ali:** So that box will be after the gateway? What will be for it...

**Prof. Rytis:** Yeah, the gateway is just for sending data, that's a gateway.

**Ali:** Yeah. Your part is this. My part is this.

**Prof. Rytis:** Yeah, yeah... Basically this.

**Ali:** And this is not my part. This is your part as well, which you need to do something with the data.

**Prof. Rytis:** Ah the last one you mean? ChirpStack and the database.

**Ali:** ChirpStack and the data...

**Prof. Rytis:** Because otherwise you're not doing anything with the data, just collecting. This is the programming and preliminary small on-device processing. And this is getting the data and some... And doing something with it.

**Ali:** So these one and these two ones.

**Prof. Rytis:** Yeah, this is just the transmission.

**Ali:** This is just a transmission.

**Prof. Rytis:** Yes.

**Ali:** And... what is my responsibility in the last two... stages of the project?

**Prof. Rytis:** In the last two stages is to actually get the data on our own box instead of using the Things Network. Because the ChirpStack provides what is the Things Network in an open source manner. Because that is limited, and whenever you want...

**Ali:** It's not customizable.

**Prof. Rytis:** Yeah, yeah. It's not customizable, and if you want more messages basically you pay a lot of money.

**Ali:** Yes.

**Prof. Rytis:** So that's not good. And to integrate AI, it's kind of also finicky. So our idea is that we have every tree itself itself in brackets, but we have our own box. And we have sensor boxes, transmission boxes, and we have processing. So these sit in the forest or house, data does not go to America or whatever... goes to this box, this box does the insights. And another benefit is that with ChirpStack you can configure packets in the way you want. Otherwise they are small kilobyte or even byte level chunks... so you saw how Ahmed was sending audio files... It's not very configurable because it only expects small packets. So if we want to let's say we have still have camera option and audio option. One way, we detect that there is something. Then we might want to wake up and enable continuous stream of audio and video here. So we can actually classify on the... on that box what is going on. Is it fully fire or maybe just I don't know, some...

**Ali:** Something else.

**Prof. Rytis:** ...something else. Because on there you cannot do that much. Just do some preliminary...

**Ali:** Because it's limited, yeah...

**Prof. Rytis:** Yeah, it's limited but... So to send through standard means, it's very time consuming because you split everything into small packets and that takes time, some get lost. With ChirpStack you can... I don't know... make a packet 100 kilobyte...

**Ali:** Yes, that is my question. You know, for example, if they have... we have full control...

**Prof. Rytis:** Okay. If we notice that there is something wrong over there in the forest, and we need more data with LoRa the payload is a few... few bytes...

**Ali:** Yes, that's also what Egidijus mentioned. We will integrate, we will have LoRa and 4G Narrowband...

**Prof. Rytis:** 4G for those... for those things that we mark as a... yeah.

**Ali:** Because anyway LoRa still requires internet connectivity to transmit somewhere else. So at least one of the... most gateways will be used LoRa based, but at least one needs to have some GSM connectivity. Because there is no Wi-Fi at the end of the forest. And we will also think maybe having multiple gateways like a mesh network, but that's more...

**Prof. Rytis:** To switch between them.

**Prof. Rytis:** Yeah, yeah.

**Ali:** Mhm.

**Prof. Rytis:** But Egidijus will try to make a universal design, where we have both the modem and LoRa... So later of course we can make variants without one or the other. But for the project we will make a universal design that has both the modem and LoRa receiver, transmitter integrated.

**Ali:** So in that way we can send high quality, high, you know... Big size data over the 4G...

**Prof. Rytis:** Even yeah, or even you know, there is a warning of forest cutting has detected and the forester might want to have a look.

**Ali:** Exactly.

**Prof. Rytis:** So you cannot do that through standard LoRa. No, no, no.

**Ali:** It's crazy. You can send separate low quality frames, but not a better quality stream.

**Prof. Rytis:** Exactly. So that ChirpStack, you can install it in that... Yeah, install, pick some Linux distribution... Or maybe there was even a build with it. I don't remember. I think you have to install something...

**Ali:** It's a Persian keyboard, sorry.

**Prof. Rytis:** Yes, and second Persian unfortunately. Not very good. It's also probably from the other way around. From right to left. Yes.

**Ali:** Yeah, it's from right to left, exactly.

**Prof. Rytis:** And list is not like just Japanese... yeah, but this is like the Things Network...

**Ali:** Yes.

**Prof. Rytis:** But it's completely open.

**Ali:** Mhm.

**Prof. Rytis:** You know, it seems like they have multiple parts... It's open source. So... so we can put standard Debian... Debian or Ubuntu?

**Ali:** Yeah. Ubuntu is heavy. I don't like it. Grab the Pig mint. It's much lighter, or any other distribution. It will run on any Debian port.

**Prof. Rytis:** Okay.

**Ali:** Pick the lightest Debian.

**Prof. Rytis:** Debian?

**Ali:** Yeah, pick the lightest Debian. For whatever it is, I personally use Mint, but that's my old habit. I tried Kubuntu with the K, yes... so so. But I think for that we can just pick the lightest Debian.

**Prof. Rytis:** Debian. Sure. Because it seems to be pre-configured for that. But you can see it runs on Raspberry, it's a light platform.

**Ali:** Yes, yes, yes, yes, yes.

**Prof. Rytis:** So we provide some you know... light web interface later on for the foresters, to see the foresters, to see the insights, the story curves and so on and that is the project.

**Ali:** So we will develop our own UI.

**Prof. Rytis:** Yeah, yeah, I think so. Because it would be Claude is very good or GPT if you like, that is good at generating user interfaces... now it's no longer a problem.

**Ali:** Exactly. I remember in 2021 I was developing a GUI, ML-based GUI...

**Prof. Rytis:** Yeah, time consuming...

**Ali:** It took three months for me to develop that. Now it is five minutes.

**Prof. Rytis:** Yes, exactly. So I think it gives us much better control than using the official TTN, standard commercial gateway and... software like Thingsboard, which again you cannot customize and as you pay 600 euros per month for the commercial license which allows you to do something.

**Ali:** So that's fine. So the next step is...

**Prof. Rytis:** And we also need to think about project evaluation. When we have our own hardware design, when we have our own software design, basically own boxes, it's much easier to pass the project. And of course we will also write some papers, this is not required for the project, but it's good for the reporting and it's hard for them to question us if we have published and it's good for us as well.

**Ali:** Exactly. Conference papers enough?

**Prof. Rytis:** Yeah probably.

**Ali:** Okay.

**Prof. Rytis:** And we also think about patenting... We spoke with Julius because it's a system and you can patent at least submit the patent... European patent not...

**Ali:** Not US.

**Prof. Rytis:** US as well, but... a big quantity of money. It's expensive.

**Ali:** Yeah.

**Prof. Rytis:** In the research world, US patent is just as good as the European patent.

**Ali:** Mhm.

**Prof. Rytis:** It's a prestigious thing.

**Ali:** Definitely it is.

**Prof. Rytis:** So might cumulate with that. And obviously go outside the commercial prototyping.

**Ali:** Mhm.

**Prof. Rytis:** Stuff like this. It's good for the prototyping but I think having a unified board is better.

**Ali:** Are you talking about the microcontroller or something?

**Prof. Rytis:** Yeah, yeah. Egidijus will design the board, you can speak also. When you have the rough ideas what is needed, you can also speak, but we already have experience in designing and ordering.

**Ali:** Yeah, he has a plan to just replace this one with the STM32...

**Prof. Rytis:** Yeah, yeah, it has done.

**Ali:** ...which has the DSP unit on it.

**Prof. Rytis:** Yeah, that's what I used in the summer for acoustic monitoring. My own variant than Ahmed's. Instead of waking up, instead of constantly listening, my solution was to peek every 800 milliseconds, just take a small peek. If anything is out of order... peek, sleep, peek, sleep... something like that.

**Ali:** Mhm, mhm.

**Prof. Rytis:** And those on the ST microchip. But I used the old one. 4. Egidijus says 5U is better maybe, but minus 14 euros. I bought it myself. So this one we will buy out of the project.

**Ali:** Okay. So, the next step is to, as we discussed before and before this contract, is to implement that bear detection... using that...

**Prof. Rytis:** Yep.

**Ali:** Using this one. That yeah, I received from the... Yeah. So this has the microphone here?

**Prof. Rytis:** Hopefully.

**Ali:** Yeah, no it is. It has, so...

**Prof. Rytis:** It should, it should. Let me show you. Yeah, it is that one we were looking for.

**Ali:** It should. So we can...

**Prof. Rytis:** Unless something is... let it should, it should. I can. It should. There was always a mic. Just magically disappeared. So the next one... The next step is to deploy the AI model on this one to test in the lab and we will proceed accordingly after this one.

**Ali:** Yep. Okay. So, there's no question from my side.

**Prof. Rytis:** Good. Well if you have questions, I'm here. Write me regarding the meeting with the forester and...

**Ali:** Sure, sure, sure.

**Prof. Rytis:** Drop the doctor...

**Ali:** Sure, thank you so much.

**Prof. Rytis:** Will show me something...

**Ali:** Okay.
