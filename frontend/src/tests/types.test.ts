import { describe, it, expect } from 'vitest';
import type { MoodClass } from '../types';

describe('Controlled Mood Vocabulary Specification', () => {
  it('strictly contains only the 7 bounded mood classes', () => {
    const controlledVocabulary: MoodClass[] = [
      'energetic',
      'positive',
      'calm',
      'neutral',
      'reflective',
      'low_energy',
      'tense'
    ];

    expect(controlledVocabulary).toHaveLength(7);
    expect(controlledVocabulary).toContain('energetic');
    expect(controlledVocabulary).toContain('positive');
    expect(controlledVocabulary).toContain('calm');
    expect(controlledVocabulary).toContain('neutral');
    expect(controlledVocabulary).toContain('reflective');
    expect(controlledVocabulary).toContain('low_energy');
    expect(controlledVocabulary).toContain('tense');
  });
});
