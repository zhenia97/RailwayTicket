import datetime
import json
import sys
import argparse
import time
import smtplib
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from email.mime.text import MIMEText
from email.header import Header


def create_args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '-from', required=True, help='Код станції відправлення (required)')
    parser.add_argument('-t', '-to', required=True, help='Код станції прибуття (required)')
    parser.add_argument('-d', '-date', required=True, help='Дата відправлення (2018-10-04) (required)')
    parser.add_argument('-time', help='Час відправлення від (00:00)')
    parser.add_argument('-tn', '-train_number', help='Номер поїзда (043К)')
    parser.add_argument('-ct', '-check_time', default=60,
                        help='Інтервал перевірки квитків у секундах. За замовчування: 60')
    parser.add_argument('-tt', '-ticket_type', choices=['П', 'К', 'Л'], help='Тип квитків: П, К, Л')
    parser.add_argument('-info', help='Код міста Київ: 2200001, Код міста Новограл-Волинський: 2200130')

    return parser.parse_args()


def get_code_by_sity(city):
    city_name = city.lower()

    if city_name == 'kyiv' or city_name == 'k':
        code = '2200001'
    elif city_name == 'novograd' or city_name == 'n':
        code = '2200130'
    else:
        code = city_name

    return code


def get_ticket_console_info():
    namespace = create_args_parser()

    if 'f' in namespace and 't' in namespace and 'd' in namespace:
        from_city = get_code_by_sity(namespace.f)
        to_city = get_code_by_sity(namespace.t)
        date = namespace.d
        time_from = namespace.time if namespace.time is not None else '00:00'
        selected_train_number = namespace.tn
        selected_ticket_type = namespace.tt
        check_time = int(namespace.ct)

        # from_city = 2200001
        # to_city = 2200130
        # date = '2018-10-04'
        # time_from = '00:00'
        # selected_train_number = '043К'
        # selected_ticket_type = 'П'
        # check_time = 60

        print('\n\nВведені параметри:\nМісто відправлення: ' + str(from_city) + '\nМісто прибуття: ' + str(to_city) +
              '\nДата: ' + str(date) + '\nЧас відправлення від: ' + str(time_from) + '\nНомер поїзда: ' + str(
            selected_train_number) +
              '\nТип місця: ' + str(selected_ticket_type) + '\nІнтервал перевірки: ' + str(check_time) + '\n\n')

        return from_city, to_city, date, time_from, selected_train_number, selected_ticket_type, check_time
    else:
        print('\nНеправильні параметри, введіть -help для довідки\n')


def send_request(from_city, to_city, date, time_from):
    url = "https://booking.uz.gov.ua/train_search/"
    request_data = {'from': from_city, 'to': to_city, 'date': date, 'time': time_from}

    request = Request(url, urlencode(request_data).encode())
    json_data = urlopen(request).read().decode()
    data = json.loads(json_data)

    return data


def parse_response(response_data, selected_train_number, selected_ticket_type):
    if 'error' in response_data:
        print('\n---ERROR---')
        print(response_data)
        sys.exit(0)

    data_list = response_data.get('data').get('list')
    parse_trains(data_list, selected_train_number, selected_ticket_type)


def parse_trains(trains, selected_train_number, selected_ticket_type):
    is_available_tickets = False
    all_success_message = ''

    for train in trains:
        places_types_arr = train.get('types')
        train_number = train.get('num')

        success_message = parse_train_places(places_types_arr, train_number, selected_train_number,
                                             selected_ticket_type)
        if success_message != '':
            all_success_message += success_message
            is_available_tickets = True

    if is_available_tickets is True:
        all_success_message = '\n\nДоступні вільні квитки!\n' + all_success_message + '\n'
        print(all_success_message)
        try:
        	send_email(all_success_message)
        	print('Повідомлення відправлено на пошту\n\n')
        except Exception as e:
        	print(e)
        
        sys.exit(1)


def parse_train_places(places_types_arr, train_number, selected_train_number, selected_ticket_type):
    success_message = ''

    if selected_train_number is None or selected_train_number == train_number:
        for place in places_types_arr:
            ticket_type = place.get('id')
            n_free_places = int(place.get('places'))

            if n_free_places > 0 and (selected_ticket_type is None or ticket_type == selected_ticket_type):
                success_message += 'Поїзд: ' + train_number.ljust(10) + 'Тип місця: ' + place.get('title').ljust(12) + \
                                   'Кількість: ' + str(n_free_places) + '\n'

    return success_message


def send_email(message):
    my_email = 'chapyname@gmail.com'
    receiver_email = 'moskovenkozhenia@gmail.com'

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('chapyname@gmail.com', '002003097chap')

    subject = 'Доступні вільні квитки'
    msg = MIMEText(message, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    server.sendmail(my_email, [receiver_email], msg.as_string())
    server.quit()


def search_loop(from_city, to_city, date, time_from, selected_train_n, selected_ticket_type, check_time):
    while True:
        data = send_request(from_city, to_city, date, time_from)
        print(str(datetime.datetime.now()))
        parse_response(data, selected_train_n, selected_ticket_type)
        time.sleep(check_time)


def main():
    from_city, to_city, date, time_from, selected_train_n, selected_ticket_type, check_time = get_ticket_console_info()
    search_loop(from_city, to_city, date, time_from, selected_train_n, selected_ticket_type, check_time)


if __name__ == '__main__':
    main()
