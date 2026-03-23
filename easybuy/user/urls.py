from django.urls import path
from . import views
from easybuy.user.views import all_products

urlpatterns = [
    path(
        "create-razorpay-order/",
        views.create_razorpay_order,
        name="create_razorpay_order",
    ),
    path(
        "verify-razorpay-payment/",
        views.verify_razorpay_payment,
        name="verify_razorpay_payment",
    ),
    path("products/", all_products, name="all_products"),
    path("profile/", views.profile_settings, name="profile_settings"),
    path("profile/addresses/", views.manage_addresses, name="manage_addresses"),
    path("profile/addresses/add/", views.user_address, name="user_address"),
    path(
        "profile/addresses/delete/<int:id>/",
        views.delete_address,
        name="delete_address",
    ),
    path("profile/addresses/edit/<int:id>/", views.edit_address, name="edit_address"),
    path("new_arrivals/", views.new_arrival, name="new_arrivals_user"),
    path("best-sellers/", views.best_seller, name="best_sellers"),
    path("products/<int:id>/", views.product_detail, name="product_detail_by_id"),
    path(
        "category/<int:id>/",
        views.category_products,
        name="category_products_by_id_user",
    ),
    path(
        "subcategory/<int:id>/",
        views.subcategory_products,
        name="subcategory_products_by_id_user",
    ),
    path(
        "category/<slug:slug>/", views.category_products, name="category_products_user"
    ),
    path(
        "subcategory/<slug:slug>/",
        views.subcategory_products,
        name="subcategory_products_user",
    ),
    path("products/<slug:slug>/", views.product_detail, name="product_detail_user"),
    path("addtocart/<int:id>/", views.addtocart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path(
        "cart/update/<int:item_id>/",
        views.update_cart_quantity,
        name="update_cart_quantity",
    ),
    path("order/success/<int:order_id>/", views.order_success, name="order_success"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("filter/", views.filtering, name="filtering"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.display_order, name="user_orders"),
    path("orders/cancel/<int:order_id>/", views.order_cancel, name="order_cancel"),
    path(
        "orders/item-cancel/<int:item_id>/",
        views.order_item_cancel,
        name="order_item_cancel",
    ),
    path("reviews/add/<int:variant_id>/", views.add_reviews, name="add_review"),
    path(
        "reviews/check-purchase/<int:variant_id>/",
        views.check_purchase_status,
        name="check_purchase_status",
    ),
    path("reviews/<int:variant_id>/", views.reviews, name="reviews"),
    path("reviews/edit/<int:review_id>/", views.edit_review, name="edit_review"),
    path("reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),
    path(
        "reviews/helpful/<int:review_id>/",
        views.toggle_review_helpful,
        name="toggle_review_helpful",
    ),
    path("buy_now/<int:variant_id>/", views.buy_now, name="buy_now"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path(
        "wishlist/<int:wishlist_id>/",
        views.specific_wishlist_view,
        name="specific_wishlist",
    ),
    path("wishlist/manage/", views.manage_wishlists, name="manage_wishlists"),
    path("wishlist/create/", views.create_wishlist, name="create_wishlist"),
    path("wishlist/edit/<int:wishlist_id>/", views.edit_wishlist, name="edit_wishlist"),
    path(
        "wishlist/delete/<int:wishlist_id>/",
        views.delete_wishlist,
        name="delete_wishlist",
    ),
    path(
        "wishlist/toggle/<int:variant_id>/<int:wishlist_id>/",
        views.toggle_wishlist,
        name="toggle_wishlist",
    ),
    path(
        "wishlist/toggle/<int:variant_id>/",
        views.toggle_wishlist,
        name="toggle_wishlist_default",
    ),
    path(
        "wishlist/remove/<int:item_id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist",
    ),
    path(
        "wishlist/move-to-cart/<int:item_id>/", views.move_to_cart, name="move_to_cart"
    ),
    path("api/brands/", views.get_brands_ajax, name="get_brands_ajax"),
    path(
        "api/subcategories/",
        views.get_subcategories_ajax,
        name="get_subcategories_ajax",
    ),
    path(
        "api/search-autocomplete/",
        views.search_autocomplete,
        name="search_autocomplete",
    ),
    path("process-cod-order/", views.process_cod_order, name="process_cod_order"),
    path("notifications/", views.all_notifications, name="all_notifications"),
]
