FROM python:3.9-buster

WORKDIR /bot

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "apollo.py" ] 