export const formatRole = (role) => {
  if (!role) return 'Unknown';
  const acronyms = ['cci', 'cwc', 'dcpu', 'wcd'];
  return role.split('_').map(word => {
    if (acronyms.includes(word.toLowerCase())) return word.toUpperCase();
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(' ');
};

export const formatString = (str) => {
  if (!str) return 'N/A';
  return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
};
