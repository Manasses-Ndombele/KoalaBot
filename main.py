from flask import Flask, request
import requests
import json
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

app = Flask(__name__)

# Variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
EXCHANGE_RATE_TOKEN = os.getenv('EXCHANGE_RATE_TOKEN')

# URLs
WEBHOOK_URL = f'https://koalabot.onrender.com/bot-webhook'
api_url = 'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}'

# Moedas aceitas
accepted_currencies = ['USD', 'BRL', 'AOA', 'BTC', 'EUR', 'GBP']

# Dados dos chats
with open('./chats.json', 'r') as json_file:
    chats_datas = json.load(json_file)

def save_chats():
    with open('chats.json', 'w') as file:
        json.dump(chats_datas, file, indent=4)

# Função para configurar o webhook
def set_webhook():
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

set_webhook()

# Função para o comando /start
def start(update: Update, context: CallbackContext):
    user_first_name = update.message.from_user.first_name
    answer = (
        f'Olá {user_first_name}, este é um Bot que serve para a conversão de moedas.\n\n'
        f'Clique na moeda que deseja converter. Temos disponíveis a conversão entre as seguintes moedas:\n\n'
        '1- /USD - Dólar Americano\n'
        '2- /BRL - Real Brasileiro\n'
        '3- /AOA - Kwanzas Angolanos\n'
        '4- /EUR - Euro da Europa\n'
        '5- /BTC - Bitcoin do Satoshi Nakamoto\n'
        '6- /GBP - Libra Esterlina do Reino Unido'
    )
    update.message.reply_text(answer)

# Função para validar a escolha da moeda
def currency_choose(update: Update, context: CallbackContext):
    currency_key = update.message.text.strip()[1:].strip()
    datas_added = False
    for chat in chats_datas['chats']:
        if chat.get('chat_id') == update.message.chat.id:
            chat['base_currency'] = currency_key
            datas_added = True

    if not datas_added:
        chats_datas['chats'].append({'chat_id': update.message.chat.id, 'base_currency': currency_key})

    save_chats()

    answer = f'Ótimo agora digite o valor na moeda que deseja converter para {currency_key}\n\nEx: 10GBP, 15000USD, 45340.23BRL, etc.\n\nOBS: Não coloque a "," como separador decimal utilize o ".", não coloque um separador de milhar.'
    update.message.reply_text(answer)

# Função para validar o valor de conversão
def verify_convertion_value(msg):
    try:
        convert_to = ''
        convert_value = ''
        for char in msg.text:
            if char.isnumeric() or char == '.':
                convert_value += char
            elif char.isalpha():
                convert_to += char

        if not convert_value.replace('.', '').isnumeric() or float(convert_value) <= 0:
            msg.reply_text("Por favor, insira um valor numérico válido para conversão.")
            return False

        if convert_to.strip().upper() not in accepted_currencies:
            msg.reply_text(f"Moeda não aceita. As moedas suportadas são: {', '.join(accepted_currencies)}.")
            return False

        # Atualiza o chat com a moeda de destino e valor
        for chat in chats_datas['chats']:
            if chat.get('chat_id') == msg.chat.id:
                chat['convert_to'] = convert_to.strip().upper()
                chat['convert_value'] = convert_value.strip()
                save_chats()
                return True

    except Exception as e:
        msg.reply_text("Ocorreu um erro ao tentar processar a conversão.")
        return False

# Função para realizar a conversão
def convertion(update: Update, context: CallbackContext):
    for chat in chats_datas['chats']:
        if chat.get('chat_id') == update.message.chat.id:
            response = requests.get(api_url.format(api_key=EXCHANGE_RATE_TOKEN, base_currency=chat.get('base_currency')))
            if response.status_code == 200:
                response_data = response.json()
                if 'conversion_rates' in response_data:
                    cambio = response_data['conversion_rates'][chat.get('convert_to')]
                    result = int(chat.get('convert_value')) / cambio
                    answer = (
                        'Conversão calculada através da ExchangeRate API\n'
                        f'1 {response_data["base_code"]} atualmente equivale a {cambio:.2f} {chat.get("convert_to")}\n'
                        f'Portanto {int(chat.get("convert_value"))} {chat.get("convert_to")} ÷ {cambio:.2f} {response_data["base_code"]} = {result:.2f} {response_data["base_code"]}'
                    )

                    update.message.reply_text(answer)

                else:
                    update.message.reply_text("Erro ao obter taxas de câmbio, tente novamente mais tarde.")
            else:
                update.message.reply_text("Erro de conexão com a API de câmbio, tente novamente mais tarde.")

        else:
            update.message.reply_text('Lamento mas não entendi a sua mensagem. Reinicie a conversa ou limpe o histórico dessa conversa e siga as instruções para obter cotações.')

# Função de erro padrão
def default_answer(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Lamento mas não consegui perceber a sua mensagem, você pode estar vendo isso pelos seguintes motivos:\n'
        'a) Você inseriu um valor inválido para ser convertido\n'
        'b) Você escolheu uma moeda de base igual a moeda de destino na conversão\n'
        '\nVocê pode tentar resolver:\n'
        'a) Apagando o histórico de conversa para si e para o chatbot e reiniciar a conversa.\n'
        'b) Ou clique aqui /start para reiniciar a conversa sem apagar o histórico.'
    )

# Webhook endpoint
@app.route('/bot-webhook', methods=['POST'])
def bot_webhook():
    data = request.get_json(force=True)
    print(f'Payload recebido: {json.dumps(data, indent=4)}')

    try:
        update = Update.de_json(data, updater.bot)
        dispatcher.process_update(update)
        print('Mensagem enviada aos handlers')
    except Exception as e:
        print(f'Erro no webhook: {e}')
    return "OK", 200

@app.route('/')
def home():
    return "KoalaBot está rodando acesse o Telegram e converse com ele."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    # Configuração do Updater e Dispatcher
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Adiciona os handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("USD", currency_choose))
    dispatcher.add_handler(CommandHandler("BRL", currency_choose))
    dispatcher.add_handler(CommandHandler("AOA", currency_choose))
    dispatcher.add_handler(CommandHandler("EUR", currency_choose))
    dispatcher.add_handler(CommandHandler("BTC", currency_choose))
    dispatcher.add_handler(CommandHandler("GBP", currency_choose))

    # Handler para valores de conversão
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, convertion))

    # Default handler
    dispatcher.add_handler(MessageHandler(Filters.text, default_answer))

    # Inicializa o Flask e o webhook
    set_webhook()

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=port)
