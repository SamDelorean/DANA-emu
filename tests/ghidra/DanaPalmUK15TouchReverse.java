// Ghidra on authentic unmodified UK1.5 updater array, based at 0x10000000.
// Static CPU ROM evidence only: never infer that an address hit is executable.
// @category Dana
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import java.io.PrintWriter;
import java.io.FileWriter;
import java.util.*;
public class DanaPalmUK15TouchReverse extends GhidraScript {
  public void run() throws Exception {
    PrintWriter out = new PrintWriter(new FileWriter(getScriptArgs()[0]));
    Memory mem=currentProgram.getMemory();
    out.println("PROGRAM="+currentProgram.getName()+" LANGUAGE="+currentProgram.getLanguageID());
    long base=0x10000000L;
    int total=0x5d0000;
    byte[] all=new byte[total];
    int got=mem.getBytes(toAddr(base),all);
    out.println("BASE=10000000 ACTUAL="+got);
    String[] names={"PF_DIR","PF_DATA","PF_SEL","PG_DIR","PG_DATA","PG_SEL","SPI2_DATA","SPI2_CTRL","ICR","IMR","PD_DATA","PD_IRQ"};
    int[] addr={0xfffff428,0xfffff429,0xfffff42b,0xfffff430,0xfffff431,0xfffff433,0xfffff800,0xfffff802,0xfffff302,0xfffff304,0xfffff419,0xfffff41d};
    for(int i=0;i<addr.length;++i){
      int value=addr[i]; int count=0;
      for(int pos=0;pos+4<=got;++pos) {
        int check=((all[pos]&255)<<24)|((all[pos+1]&255)<<16)|((all[pos+2]&255)<<8)|(all[pos+3]&255);
        if(check==value) {
          count++;
          if(count<=35){
            out.printf("HIT %-12s ROM=%08X bytes=",names[i],base+pos);
            int low=Math.max(pos-8,0),hi=Math.min(pos+12,got);
            for(int p=low;p<hi;p++)out.printf("%02X",all[p]&255);
            out.println();
          }
        }
      }
      out.printf("TOTAL %-12s %d\n",names[i],count);
    }
    // 68000 absolute-word MMIO uses sign-extended 16-bit 0xFxxx, so search
    // both absolute LONG (above) and absolute WORD encodings.
    int[] abw={0xf428,0xf429,0xf42b,0xf430,0xf431,0xf433,0xf800,0xf802,0xf302,0xf304,0xf419,0xf41d};
    for(int i=0;i<abw.length;i++){
      int count=0;
      for(int j=0;j+2<=got;j++){
        int w=(all[j]&255)<<8 | (all[j+1]&255);
        if(w==abw[i]){
          count++;
          if(count<=60) {
            out.printf("WORD_HIT %-12s ROM=%08X before=",names[i],base+j);
            for(int k=Math.max(0,j-8);k<Math.min(j+8,got);k++)out.printf("%02X",all[k]&255);
            out.println();
          }
        }
      }
      out.printf("WORD_TOTAL %-12s %d\n",names[i],count);
    }
    // Search absolute-long function pointer data for the digitizer's SPI2 routine.
    for(long target:new long[]{0x1007b0b8L,0x1007b0beL,0x1007b10cL,0x10079766L}){
      int count=0;
      for(int j=0;j+4<=got;j++) {
        long v=((long)(all[j]&255)<<24)|((long)(all[j+1]&255)<<16)|((long)(all[j+2]&255)<<8)|(all[j+3]&255);
        if(v==target){ count++;if(count<=40) out.printf("PTR %08X at=%08X\n",target,base+j); }
      }
      out.printf("PTR_TOTAL %08X %d\n",target,count);
    }
    long[] sites={0x1007f320L,0x1007f3c0L,0x1007f400L,0x1007b5e0L,0x1007b070L,0x1007b0b8L,0x1007b10cL,0x10079710L};
    for(long site:sites){
      out.printf("CODE_START=%08X\n",site);
      long pc=site;
      for(int n=0;n<48;n++){
        Instruction ins=getInstructionAt(toAddr(pc));
        if(ins==null){
          try { disassemble(toAddr(pc)); } catch(Exception e) {}
          ins=getInstructionAt(toAddr(pc));
        }
        if(ins==null){out.printf("%08X UNDECODED\n",pc);pc+=2;continue;}
        out.printf("%08X %s\n",pc,ins.toString());
        pc+=ins.getLength();
      }
    }
    out.close(); println("DANA_PALM_UK15_TOUCH_REVERSE_DONE");
  }
}
