from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    IP клиента.

    За nginx request.client.host — адрес самого nginx. Реальный IP nginx кладёт в
    X-Real-IP (`$remote_addr`, клиент подделать его не может: nginx перезаписывает
    заголовок). X-Forwarded-For брать нельзя: nginx лишь ДОПИСЫВАЕТ к нему адрес,
    а первое значение приходит от клиента, и им можно обойти любой лимит по IP.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"
