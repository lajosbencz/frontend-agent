// One Pinia store instance per domain (brewcraft/emporium/vendor), so state never mixes across
// demos. Memoizes the store definition per domain and returns its instance.
export function perDomainStore<Use extends () => unknown>(define: (domain: string) => Use) {
  const cache = new Map<string, Use>()
  return (domain: string): ReturnType<Use> => {
    let use = cache.get(domain)
    if (!use) {
      use = define(domain)
      cache.set(domain, use)
    }
    return use() as ReturnType<Use>
  }
}
