FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SCML_STATE_DIR=/state
WORKDIR /app
COPY requirements.lock pyproject.toml LICENSE ./
COPY packages ./packages
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home scml && mkdir /state && chown scml:scml /state
COPY apps/api ./apps/api
COPY apps/__init__.py ./apps/__init__.py
COPY data/sample ./data/sample
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
