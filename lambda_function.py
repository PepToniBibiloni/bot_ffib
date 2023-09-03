import re
import requests
from bs4 import BeautifulSoup
import os

LOGIN_URL = "https://intranet.ffib.es/nfg/NLogin"
TARGET_URL = "https://intranet.ffib.es/nfg/NPcd/GCorreos_Listado?cod_primaria=5000221&cod_buzon=0&ModoCorreo=0"
TELEGRAM_BOT_TOKEN = os.environ.get("FFIB_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("FFIB_CHAT_ID")
USR = os.environ.get("FFIB_USR")
PSW = os.environ.get("FFIB_PSW")

def login(session, username, password):
    login_data = {
        "NUser": username,
        "NPass": password,
        "LoginAjax": "1",
        "N_Ajax": "1"
    }
    response = session.post(LOGIN_URL, data=login_data, verify=False)
    return response

def get_target_content(session):
    response = session.get(TARGET_URL)
    return response.text if response.status_code == 200 else None

def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(telegram_url, data=data, verify=False)
    return response

def send_telegram_file(files):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    data = {'chat_id': TELEGRAM_CHAT_ID}
    response = requests.post(telegram_url, data=data,files=files, verify=False)
    return response

def main():
    session = requests.Session()
    
    try:
        response_login = login(session, USR, PSW)
        if response_login.status_code == 200:
            target_content = get_target_content(session)
            if target_content:
                soup = BeautifulSoup(target_content, "html.parser")
                target_table = soup.find("table", class_="table table-striped table-hover table-bordered")
                if target_table:
                    tr_elements = target_table.find_all("tr")
                    tr_elements = [tr for tr in tr_elements if tr.td]
                    pattern = r"javascript:Abrir_Correo\('([^']+)','([^']+)'\);"
 
                    for tr in tr_elements:
                        first_td = tr.find("td", style="vertical-align: middle;border-right:0px !important;")
                        match = re.search(pattern, first_td.a['href'])
                        td = tr.find_all("td")
                        if match:
                            if td and '----------' in td[2].get_text():
                                url_adicional = f"https://intranet.ffib.es/nfg/NPcd/{match.group(1)}"
                                response_adicional = session.get(url_adicional)
                                if response_adicional.status_code == 200:
                                    html_adicional = response_adicional.text
                                    soup_adicional = BeautifulSoup(html_adicional, "html.parser")
                                    td_asunto_element = soup_adicional.find("td", id="tdAsunto")
                                    asunto_contenido = td_asunto_element.get_text(strip=True) if td_asunto_element else ""
                                    descripcion_td = soup_adicional.find("td", class_="BG_TIT_PAG")
                                    descripcion_contenido = descripcion_td.get_text(strip=True) if descripcion_td else ""
                                    send_telegram_message(f"{asunto_contenido}\n\n{descripcion_contenido}")
                                    download_links = soup_adicional.find_all('a',attrs={"title":'Descargar fichero'})
                                    if download_links:
                                        for id,link in enumerate(download_links):
                                            rs_files = session.get(f'https://intranet.ffib.es/nfg/NPcd/GCorreos_Descarga?cod_primaria=5000221&cod_correo={match.group(2)}&Registro=0&fichero={id+1}');
                                            if rs_files.status_code == 200:
                                                file = {'document': (f'documento{id}.pdf', rs_files.content)}
                                                send_telegram_file(file)
    except requests.RequestException as e:
        send_telegram_message(f"An error occurred: {str(e)}")                 

def lambda_handler(event, context):
    return main()

