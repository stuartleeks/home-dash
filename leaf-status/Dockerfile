FROM python:3.11.7

WORKDIR /app

# Don't write pyc files to disk: https://docs.python.org/3/using/cmdline.html#cmdoption-B
ENV PYTHONDONTWRITEBYTECODE 1
# Don't buffer stdout and stderr: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED 1


COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Temp until https://github.com/filcole/pycarwings2/pull/47 is merged/released
RUN sed -i 's/api_v210707_/api_v230317_/g' /usr/local/lib/python3.11/site-packages/pycarwings2/pycarwings2.py

COPY . .

# CMD ["python3", "get-leaf-summary.py"]
