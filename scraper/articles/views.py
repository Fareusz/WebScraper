from rest_framework import generics
from .models import Article
from .serializers import ArticleSerializer


class ArticleListView(generics.ListAPIView):
    """Read-only endpoint returning articles.

    Supports optional filtering with ?source=<domain> which filters by
    `url__icontains`.
    """
    serializer_class = ArticleSerializer

    def get_queryset(self):
        qs = Article.objects.all()
        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(url__icontains=source)
        return qs


class ArticleRetrieveView(generics.RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
