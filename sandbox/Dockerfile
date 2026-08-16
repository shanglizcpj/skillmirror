FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    sandbox

WORKDIR /runner

COPY runner.py /runner/runner.py

RUN chown -R sandbox:sandbox /runner \
    && chmod 0555 /runner/runner.py

USER 10001:10001

ENTRYPOINT ["python", "-I", "-S", "/runner/runner.py"]