from django.urls import path, include
from .auth_urls import urlpatterns as auth_urls
from products.urls import urlpatterns as products_urls
from customers.urls import urlpatterns as customers_urls
from cart.urls import urlpatterns as cart_urls
from inventory.urls import urlpatterns as inventory_urls
from payments.urls import urlpatterns as payments_urls
from orders.urls import urlpatterns as orders_urls
from promotions.urls import urlpatterns as promotions_urls
from recommendations.urls import urlpatterns as recommendations_urls

version = 'v1'

urlpatterns = [
    path(f'{version}/auth/', include(auth_urls), name='Authentication'),
    path(f'{version}/products/', include(products_urls), name='Products'),
    path(f'{version}/customers/', include(customers_urls), name='Customers'),
    path(f'{version}/inventory/', include(inventory_urls), name='Inventory'),
    path(f'{version}/payments/', include(payments_urls), name='Payments'),
    path(f'{version}/orders/', include(orders_urls), name='Orders'),
    path(f'{version}/promotions/', include(promotions_urls), name='Promotions'),
    path(f'{version}/recommendations/', include(recommendations_urls), name='Recommendations'),
    path(f'{version}/', include(cart_urls), name='Cart'),
]
