"""
Celery Tasks for Recommendations App
"""
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='recommendations.tasks.update_product_recommendations')
def update_product_recommendations():
    """
    Periodic task to precompute product recommendations.
    Runs every hour via Celery Beat.
    """
    from products.models import Product
    from customers.models import Customer
    from recommendations.views import RecommendationEngine

    logger.info("Starting product recommendations update")

    try:
        engine = RecommendationEngine()
        products_updated = 0
        customers_updated = 0

        # Precompute content-based recommendations for active products
        active_products = Product.objects.filter(is_active=True).values_list('id', flat=True)[:100]

        for product_id in active_products:
            try:
                recommendations = engine.get_content_based_recommendations(product_id, limit=10)
                # Cache is set inside the method
                products_updated += 1
            except Exception as e:
                logger.error(f"Error updating recommendations for product {product_id}: {str(e)}")

        # Precompute personalized recommendations for active customers
        # Limit to customers who have made purchases or have recent activity
        cutoff_date = timezone.now() - timedelta(days=90)
        active_customers = Customer.objects.filter(
            is_active=True,
            total_orders__gt=0,
            last_login__gte=cutoff_date
        ).values_list('id', flat=True)[:500]

        for customer_id in active_customers:
            try:
                recommendations = engine.get_personalized_recommendations(customer_id, limit=10)
                customers_updated += 1
            except Exception as e:
                logger.error(f"Error updating recommendations for customer {customer_id}: {str(e)}")

        logger.info(f"Recommendations update completed: {products_updated} products, {customers_updated} customers")

        return {
            'status': 'success',
            'products_updated': products_updated,
            'customers_updated': customers_updated
        }

    except Exception as e:
        logger.error(f"Error in update_product_recommendations task: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='recommendations.tasks.update_trending_cache')
def update_trending_cache():
    """
    Update trending products cache.
    Runs every 15 minutes via Celery Beat.
    """
    from recommendations.views import RecommendationEngine

    logger.info("Starting trending products cache update")

    try:
        engine = RecommendationEngine()

        # Update trending for different time periods
        time_periods = [1, 7, 30]  # 1 day, 1 week, 1 month

        for days in time_periods:
            trending_ids = engine.get_trending_products(limit=50, days=days)
            cache_key = f'trending_{50}_{days}_None'
            cache.set(cache_key, trending_ids, 1800)  # 30 minutes

        logger.info(f"Trending cache updated for {len(time_periods)} time periods")

        return {'status': 'success', 'time_periods': time_periods}

    except Exception as e:
        logger.error(f"Error in update_trending_cache task: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='recommendations.tasks.cleanup_old_interactions')
def cleanup_old_interactions(days=180):
    """
    Clean up old product interactions to keep database lean.
    Runs monthly.

    Args:
        days: Delete interactions older than this many days
    """
    from recommendations.models import ProductInteraction, RecommendationLog

    logger.info(f"Starting cleanup of interactions older than {days} days")

    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        # Delete old interactions
        interactions_deleted = ProductInteraction.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        # Delete old recommendation logs
        logs_deleted = RecommendationLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleanup completed: {interactions_deleted} interactions, {logs_deleted} logs deleted")

        return {
            'status': 'success',
            'interactions_deleted': interactions_deleted,
            'logs_deleted': logs_deleted
        }

    except Exception as e:
        logger.error(f"Error in cleanup_old_interactions task: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='recommendations.tasks.generate_recommendation_report')
def generate_recommendation_report():
    """
    Generate daily recommendation engine performance report.
    Runs daily at 2 AM.
    """
    from recommendations.models import RecommendationLog, ProductInteraction
    from django.db.models import Count, Avg

    logger.info("Starting recommendation performance report generation")

    try:
        # Get yesterday's data
        yesterday = timezone.now() - timedelta(days=1)
        start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Total recommendations shown
        total_recs = RecommendationLog.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day
        ).count()

        # Total clicks
        logs_with_clicks = RecommendationLog.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day,
            clicked_products__isnull=False
        )

        total_clicks = sum(len(log.clicked_products) for log in logs_with_clicks)

        # Conversion count
        total_conversions = RecommendationLog.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day,
            conversion=True
        ).count()

        # Performance by type
        performance_by_type = RecommendationLog.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day
        ).values('recommendation_type').annotate(
            count=Count('id'),
            conversions=Count('id', filter=Q(conversion=True))
        )

        # Interactions
        total_interactions = ProductInteraction.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day
        ).count()

        report = {
            'date': yesterday.date().isoformat(),
            'total_recommendations': total_recs,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'total_interactions': total_interactions,
            'ctr': (total_clicks / (total_recs * 10) * 100) if total_recs > 0 else 0,
            'conversion_rate': (total_conversions / total_recs * 100) if total_recs > 0 else 0,
            'performance_by_type': list(performance_by_type)
        }

        logger.info(f"Recommendation report generated for {yesterday.date()}")
        logger.info(f"Report: {report}")

        # TODO: Send report via email to admins
        # send_mail(...)

        return {'status': 'success', 'report': report}

    except Exception as e:
        logger.error(f"Error in generate_recommendation_report task: {str(e)}")
        return {'status': 'error', 'message': str(e)}

