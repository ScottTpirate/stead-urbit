// Urbit's small-size (detail: none) symbol index. See PROVENANCE.md and vendor/urbit-sigil.
// Identical upstream paths are stored once. Each syllable still selects its original shape.
export interface ShipGlyph {
  readonly kind: 'circle' | 'rect' | 'path';
  readonly d?: string;
  readonly border: boolean;
  readonly prefixes: string;
  readonly suffixes: string;
}

export const shipGlyphs: readonly ShipGlyph[] = [
  {
    kind: 'circle', border: true,
    prefixes: 'bar bol dar dib dol dop doz fol fop hap har hol hop lar lib lig lop mar mol mop nar nib nol nop par pol rib rig rol rop sar sib sig sol sop tap tar tol top wol',
    suffixes: 'bet dem det dul fed fet ful het hul led let lun med met mul mun ned nem net nul ped pem pet pun red rem ret rul sed sem set sul ted tem tul wed wet zod',
  },
  {
    kind: 'circle', border: false,
    prefixes: '',
    suffixes: 'sun',
  },
  {
    kind: 'path', border: true,
    d: 'M0 0C0 70.6925 57.3075 128 128 128V0H0Z',
    prefixes: 'bac ban bat bic bid bis bos dab dac dap dat dif dir dos fab fid fir hab hac hat hav hid hos lac lap lat lid los mac mat mid mir mos nac nat nav nid nos pac pad pan pat pid pos rap rav rid ros sab san sap sat sic sid tab tac tad tan tic tid tir wac wan wat wid wis',
    suffixes: 'ryl',
  },
  {
    kind: 'path', border: true,
    d: 'M0 127.946C0.0292286 57.2783 57.3256 3.08928e-06 128 0C128 70.6823 70.7089 127.984 0.0305092 128C0.0203397 128 0.01017 128 2.36469e-09 128L0 127.946Z',
    prefixes: 'doc fal hal soc wal wit',
    suffixes: 'bel byr del dyr fel fyr lyr mel myr nel nyr pel rel sel syr tel tyr tyv wel',
  },
  {
    kind: 'path', border: true,
    d: 'M0 64L5.59506e-06 0L128 1.11901e-05V64C128 99.3462 99.3462 128 64 128C28.6538 128 -4.6351e-06 99.3462 0 64Z',
    prefixes: '',
    suffixes: 'der dur per ser ter wer',
  },
  {
    kind: 'path', border: true,
    d: 'M0.0541 0C70.7217 0.0292317 128 57.3256 128 128C57.3177 128 0.0164917 70.7089 7.62806e-06 0.0305091C7.62851e-06 0.0203397 -4.44317e-10 0.01017 0 0H0.0541Z',
    prefixes: 'bal bit dal fit lit loc mal mit moc nal pal pit poc rac ral rit roc sal sit tal toc',
    suffixes: 'def lyd nyd ref ryd sef syd tyd wyd',
  },
  {
    kind: 'path', border: true,
    d: 'M128 0C57.3075 8.42999e-07 -8.42999e-07 57.3075 0 128H128V0Z',
    prefixes: 'bon dis don fog fon lab lad lav lon map mip mis mog mon nap nis pon rab ris ron sog son tip tog ton wic',
    suffixes: 'bep dep des fes hes lep mep nes pes rep res sep tep tes wep wes',
  },
  {
    kind: 'path', border: true,
    d: 'M128 128C128 57.3076 70.6925 6.18013e-06 1.11901e-05 0L0 128L128 128Z',
    prefixes: 'lis mic pic rad ric',
    suffixes: 'bec bes bud bus dec duc dus dyl dys fep fus hec hep hus lec luc lud lur lus lys mec mes mud mur mus nec nep nub num nus nux nyl nys pec pub pyl rec ruc rud rus rux ryc rys sec sub sud sur tec tuc tud tus tux tyc tyl wyc wyl',
  },
  {
    kind: 'path', border: true,
    d: 'M128 64V128H0L2.79753e-06 64C4.34256e-06 28.6538 28.6538 -1.54503e-06 64 0C99.3462 1.54503e-06 128 28.6538 128 64Z',
    prefixes: 'hob nim sim tim tob',
    suffixes: 'fun tun',
  },
  {
    kind: 'path', border: true,
    d: 'M5.59506e-06 128C70.6925 128 128 70.6925 128 0L0 5.59506e-06L5.59506e-06 128Z',
    prefixes: 'fad fos had han',
    suffixes: 'bur byl byn dux dyn fur fyl fyn lux lyn lyx myl myn nym nyx pur pyx rum ryg rym ryn ryp ryx sum syl sym syn syp syx tyn typ wyn wyx',
  },
  {
    kind: 'path', border: true,
    d: 'M64 0H128V128H64C28.6538 128 0 99.3462 0 64C0 28.6538 28.6538 0 64 0Z',
    prefixes: 'bil bor bot dan dav dig dil dor dot fam fan fig fil fip fod for fot hil hoc hod lag lan lod lor mag mig mil mod mor mot nam nil noc nod nor pag pil pod rag ram ran ril rip sam sav sil sor tag tam til tod tor wor',
    suffixes: '',
  },
  {
    kind: 'path', border: true,
    d: 'M64 128H0L5.59506e-06 -7.62939e-06L64 -2.03434e-06C99.3462 1.05573e-06 128 28.6538 128 64C128 99.3462 99.3462 128 64 128Z',
    prefixes: '',
    suffixes: 'lug lup nex nup ryt',
  },
  {
    kind: 'path', border: true,
    d: 'M64 128H0L5.59506e-06 0L64 5.59506e-06C99.3462 8.68512e-06 128 28.6538 128 64C128 99.3462 99.3462 128 64 128Z',
    prefixes: '',
    suffixes: 'ber bex byt dev dex dun dyt fer fex hex ler lev lex lyt mer mev mex mug ner nev nyt pex rev rex run rup sev sug sup syt tev tex tug wex wyt',
  },
  {
    kind: 'rect', border: true,
    prefixes: 'bin das din div dov fas fin has hin las lin liv lom mas min nom nov pas pin rin riv rov sip siv som sov tas tin tom win',
    suffixes: 'ben deb deg den dut feb fen heb hut leb leg len lut meb meg mut neb nut peg pen put reb reg ren rut seb seg sen sut teb teg ten web weg wen',
  },
];
