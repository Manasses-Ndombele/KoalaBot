from flask import Flask, request
import telebot
import requests
import json
import os

app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
EXCHANGE_RATE_TOKEN = os.getenv('EXCHANGE_RATE_TOKEN')
koala_bot = telebot.TeleBot(TELEGRAM_TOKEN)
WEBHOOK_URL = f'https://koalabot.onrender.com/bot-webhook'
webhook_info = requests.get(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo"
).json()

if webhook_info.get("result", {}).get("url") != WEBHOOK_URL:
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
        data={"url": WEBHOOK_URL},
    )

    print(f'Webhook configurado: {response.json()}')

else:
    print("Webhook já está configurado.")

api_url = 'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}'
accepted_currencies = ['USD', 'BRL', 'AOA', 'BTC', 'EUR', 'GBP']
with open('./chats.json', 'r') as json_file:
    chats_datas = json.load(json_file)

def save_chats():
    with open('chats.json', 'w') as file:
        json.dump(chats_datas, file, indent=4)

def verify_convertion_value(msg):
    try:
        convert_to = ''
        convert_value = ''
        for char in msg.text:
            if char.isnumeric() or char == '.':
                convert_value += char

            elif char.isalpha():
                convert_to += char

        if not convert_value.replace('.', '').isnumeric():
            return False

        if convert_to.strip().upper() in accepted_currencies:
            for chat in chats_datas['chats']:
                if chat.get('chat_id') == msg.chat.id:
                    chat['convert_to'] = convert_to
                    chat['convert_value'] = convert_value
                    save_chats()
                    return True

    except Exception as e:
        return False

@koala_bot.message_handler(func=verify_convertion_value)
def convertion(msg):
    for chat in chats_datas['chats']:
        if chat.get('chat_id') == msg.chat.id:
            response = requests.get(api_url.format(api_key=EXCHANGE_RATE_TOKEN, base_currency=chat.get('base_currency')))
            if response.status_code == 200:
                response_data = response.json()
                cambio = response_data['conversion_rates'][chat.get('convert_to')]
                result = int(chat.get('convert_value')) / cambio
                answer = (
                    'Conversão calculada através da ExchangeRate API\n'
                    f'1 {response_data["base_code"]} atualmente equivale a {cambio:.2f} {chat.get("convert_to")}\n'
                    f'Portanto {int(chat.get("convert_value"))} {chat.get("convert_to")} ÷ {cambio:.2f} {response_data["base_code"]} = {result:.2f} {response_data["base_code"]}'
                )

                koala_bot.reply_to(msg, answer)
                with open('./automation.ogg', 'rb') as audio_file:
                    koala_bot.send_voice(msg.chat.id, voice=audio_file, caption='Muito obrigado!')

            else:
                answer = 'A requesição a ExchangeRate API não foi realizada com sucesso! Reinicie a conversa e tente novamente.'
                koala_bot.reply_to(msg, answer)

        else:
            answer = 'Lamento mas não entendi a sua mensagem. Reinicie a conversa ou limpe o histórico dessa conversa e siga as instruções para obter cotações.'
            koala_bot.reply_to(msg, answer)

@koala_bot.message_handler(commands=accepted_currencies)
def currency_choose(msg):
    currency_key = msg.text.strip()[1:].strip()
    datas_added = False
    for chat in chats_datas['chats']:
        if chat.get('chat_id') == msg.chat.id:
            chat['base_currency'] = currency_key
            datas_added = True

    if not datas_added:
        chats_datas['chats'].append({'chat_id': msg.chat.id, 'base_currency': currency_key})

    save_chats()
    answer = f'Ótimo agora digite o valor na moeda que deseja converter para {currency_key}\n\nEx: 10GBP, 15000USD, 45340.23BRL, etc.\n\nOBS: Não coloque a "," como separador decimal utilize o ".", não coloque um separador de milhar.'
    koala_bot.reply_to(msg, answer)

@koala_bot.message_handler(commands=['start'])
def start_answer(msg):
    answer = (
        f'Olá {msg.from_user.first_name}, este é um Bot que serve para a conversão de moedas.\n\n'
        f'Clique na moeda que deseja converter. Temos disponíveis a conversão entre as seguintes moedas:\n\n'
        '1- /USD - Dólar Americano\n'
        '2- /BRL - Real Brasileiro\n'
        '3- /AOA - Kwanzas Angolanos\n'
        '4- /EUR - Euro da Europa\n'
        '5- /BTC - Bitcoin do Satoshi Nakamoto\n'
        '6- /GBP - Libra Esterlina do Reino Unido'
    )

    koala_bot.send_message(msg.chat.id, answer)

def default_msg(msg):
    return True

@koala_bot.message_handler(func=default_msg)
def default_answer(msg):
    answer = (
        'Lamento mas não consegui perceber a sua mensagem, você pode estar vendo isso pelos seguintes motivos:\n'
        'a) Você inseriu um valor inválido para ser convertido\n'
        'b) Você escolheu uma moeda de base igual a moeda de destino na conversão\n'
        '\nVocê pode tentar resolver:\n'
        'a) Apagando o histórico de conversa para si e para o chatbot e reiniciar a conversa.\n'
        'b) Ou clique aqui /start para reiniciar a conversa sem apagar o histórico.'
    )

    koala_bot.send_message(msg.chat.id, answer)

@app.route('/bot-webhook', methods=['POST'])
def bot_webhook():
    update = telebot.types.Update.de_json(request.get_json(force=True))
    koala_bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def home():
    return "KoalaBot está rodando acesse o Telegram e converse com ele."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
