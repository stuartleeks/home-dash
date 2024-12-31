FROM python:3.12

WORKDIR /app

# Don't write pyc files to disk: https://docs.python.org/3/using/cmdline.html#cmdoption-B
ENV PYTHONDONTWRITEBYTECODE 1
# Don't buffer stdout and stderr: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED 1

# Pillow/uvicorn install takes a while so front-load and cache!
RUN pip install Pillow
RUN pip install uvicorn[standard]

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
