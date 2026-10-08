// 按页拉全量，直到超过 total_page
export const collectPages = async <T>(
  load: (currentPage: number) => Promise<{ list: T[]; totalPage: number }>,
): Promise<T[]> => {
  const collected: T[] = []
  let currentPage = 1
  let totalPage = 1
  do {
    const page = await load(currentPage)
    collected.push(...page.list)
    totalPage = page.totalPage || 0
    currentPage += 1
  } while (currentPage <= totalPage)
  return collected
}
