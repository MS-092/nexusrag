export interface SkillInfo {
  name: string;
  description: string;
  usage: string;
}

/** Skills to suggest while the user is still typing the command word (e.g. "/su"). */
export function matchingSkills(
  input: string,
  skills: SkillInfo[],
): SkillInfo[] {
  const match = /^\/([A-Za-z0-9_-]*)$/.exec(input);
  if (!match) return [];
  const prefix = match[1].toLowerCase();
  return skills.filter((s) => s.name.startsWith(prefix));
}
