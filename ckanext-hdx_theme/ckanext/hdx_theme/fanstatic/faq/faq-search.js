(function() {
  const SEARCH_BASE_SELECTOR='.wrapper-primary';
  function _resetSearch($panel) {
    $panel.find("span.highlight").closest(".faq-panel-collapse").collapse('hide');
    $panel.unhighlight();
    $("#search-no-results").hide();
    $("#search-results").hide();
  }

  function updateSearch() {
    const text = $(this).val();
    console.log(text);
    const $panel = $(SEARCH_BASE_SELECTOR);
    _resetSearch($panel);
    $panel.highlight(text);
    const $results = $panel.find("span.highlight");
    if ($results.length > 0) {
      $results.closest(".faq-panel-collapse").collapse('show');
      $results.first().get(0).scrollIntoView({ behavior: 'smooth' });
      $("#faq-search-current").text('0');
      $("#faq-search-total").text($results.length);
      incrementCurrentResult(1)();
      $("#search-results").show();
    } else {
      $("#search-no-results").show();
    }
  }

  function incrementCurrentResult(val) {
    return () => {
      $("span.highlight.current").removeClass("current");
      let result = parseInt($("#faq-search-current").text());
      let total = parseInt($("#faq-search-total").text());
      result += val;
      result = (result < 1 ? total : (result > total ? 1 : result));
      $("#faq-search-current").text(result);
      const current = $(SEARCH_BASE_SELECTOR).find("span.highlight").get(result - 1);
      $(current).addClass("current");
      current.scrollIntoView({ behavior: 'smooth' });
      return false;
    }
  }

  $(document).ready(function(){
    $("#faq-search").change(updateSearch);
    $("#faq-search-prev").click(incrementCurrentResult(-1));
    $("#faq-search-next").click(incrementCurrentResult(1));
  });
}).call(this);
